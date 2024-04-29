# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import asyncio
import dataclasses
import datetime
import enum
import pathlib
import re
import typing
from collections.abc import Sequence

import httpx

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.ignore import IgnoreList
from kitsunekko_tools.kitsu_parse import find_all_subtitle_dirs, find_all_subtitle_files
from kitsunekko_tools.kitsu_types import AnimeDir, SubtitleFile


def is_file_non_empty(file_path: pathlib.Path) -> bool:
    """
    Returns True if file exists and is not empty.
    """
    return file_path.is_file() and file_path.stat().st_size > 0


class PageCrawlResult(typing.NamedTuple):
    visited_dir: AnimeDir
    found_dirs: list[AnimeDir]
    found_files: list[SubtitleFile]

    def __str__(self) -> str:
        return str(
            f"visited page {self.visited_dir.url}. "
            f"found {len(self.found_files)} files. "
            f"found {len(self.found_dirs)} directories."
        )


@dataclasses.dataclass
class LocalSubtitleFile:
    remote: SubtitleFile  # remote URL
    file_path: pathlib.Path  # path to the file on the hard drive

    def __init__(self, remote: SubtitleFile, config: KitsuConfig):
        self.remote = remote
        self.file_path = config.destination / remote.show_name / remote.file_name

    def ensure_subtitle_dir(self) -> None:
        """
        Create directory to store the subtitle file.
        """
        return self.file_path.parent.mkdir(exist_ok=True)

    def is_already_downloaded(self) -> bool:
        return is_file_non_empty(self.file_path)


class DownloadStatus(enum.Enum):
    already_exists = enum.auto()
    explicitly_ignored = enum.auto()
    download_failed = enum.auto()
    saved = enum.auto()

    def __str__(self) -> str:
        return self.name.replace("_", " ")


@dataclasses.dataclass(frozen=True)
class DownloadResult:
    reason: DownloadStatus
    subtitle: LocalSubtitleFile
    status_code: int = 0

    def __repr__(self):
        if self.reason == DownloadStatus.download_failed:
            return f"{self.reason} with status {self.status_code}: {self.subtitle.remote.url}"
        return f"{self.reason}: {self.subtitle.remote.url}"

    def is_successful(self) -> bool:
        return self.reason == DownloadStatus.already_exists or self.reason == DownloadStatus.saved


@dataclasses.dataclass(frozen=True)
class FetchResult:
    to_visit: set[AnimeDir]
    to_download: set[SubtitleFile]
    visited: set[AnimeDir]
    saved: set[LocalSubtitleFile]
    failed: set[LocalSubtitleFile]

    @classmethod
    def new(cls):
        return cls(to_visit=set(), to_download=set(), visited=set(), saved=set(), failed=set())

    def update(self, dir_result: PageCrawlResult, downloads: Sequence[DownloadResult]):
        self.to_visit.update(dir_result.found_dirs)
        self.to_download.update(dir_result.found_files)
        self.visited.add(dir_result.visited_dir)
        self.saved.update(f.subtitle for f in downloads if f.reason == DownloadStatus.saved)
        self.failed.update(f.subtitle for f in downloads if f.reason == DownloadStatus.download_failed)

    def __str__(self) -> str:
        return str(
            f"visited {len(self.visited)} pages. "
            f"saved {len(self.saved)} files. "
            f"failed {len(self.failed)} files."
        )


@dataclasses.dataclass(frozen=True)
class FetchState:
    to_visit: set[AnimeDir]
    visited: set[AnimeDir]

    @classmethod
    def new(cls, download_root_url: str) -> typing.Self:
        return cls(
            to_visit={
                AnimeDir(download_root_url, "subtitles", datetime.datetime.now()),
            },
            visited=set(),
        )

    def balance(self, prev_result: FetchResult) -> None:
        self.visited.update(self.to_visit)
        self.to_visit.clear()
        self.to_visit.update(prev_result.to_visit - self.visited)

    def has_unvisited(self) -> bool:
        return len(self.to_visit) > 0


@dataclasses.dataclass(frozen=True)
class DownloadError(KitsuException):
    url: str

    @property
    def what(self) -> str:
        return type(self.__cause__).__name__


def get_anime_title(page_text: str) -> str:
    title = re.search(r"<title>([^<>]+)</title>", page_text, flags=re.IGNORECASE | re.MULTILINE).group(1)
    title = title.replace(" - Japanese subtitles - kitsunekko.net", "").replace("/", " ").replace("\\", " ")
    return title.strip()


def get_http_client(config: KitsuConfig):
    return httpx.AsyncClient(
        proxies=config.proxy,
        headers=config.headers,
        timeout=config.timeout,
        follow_redirects=False,
    )


class Sync:
    _config: KitsuConfig
    _ignore: IgnoreList
    _now: datetime
    _full_sync: bool

    def __init__(self, config: KitsuConfig, full_sync: bool = False):
        self._config = config
        self._config.raise_for_destination()
        self._ignore = IgnoreList(self._config)
        self._now = datetime.datetime.now()
        self._full_sync = full_sync

    async def download_sub(self, client: httpx.AsyncClient, subtitle: LocalSubtitleFile) -> DownloadResult:
        if subtitle.is_already_downloaded():
            return DownloadResult(DownloadStatus.already_exists, subtitle)

        if self._ignore.is_matching(subtitle.file_path):
            return DownloadResult(DownloadStatus.explicitly_ignored, subtitle)

        try:
            r = await client.get(subtitle.remote.url)
        except Exception as e:
            raise DownloadError(subtitle.remote.url) from e

        if r.status_code != httpx.codes.OK:
            return DownloadResult(DownloadStatus.download_failed, subtitle, r.status_code)

        subtitle.ensure_subtitle_dir()
        print(f"downloading file: {subtitle.remote.url}")
        with open(subtitle.file_path, "wb") as f:
            f.write(r.content)
        return DownloadResult(DownloadStatus.saved, subtitle, r.status_code)

    async def download_subs(
        self, client: httpx.AsyncClient, to_download: Sequence[SubtitleFile]
    ) -> Sequence[DownloadResult]:
        tasks = tuple(self.download_sub(client, LocalSubtitleFile(sub, self._config)) for sub in to_download)
        results = []
        for fut in asyncio.as_completed(tasks):
            try:
                result = await fut
            except DownloadError as ex:
                print(f"got {ex.what} while trying to download {ex.url}")
            else:
                print(result)
                if result.is_successful():
                    # this file will not be downloaded again even if it is moved later.
                    self._ignore.add_file(result.subtitle.file_path)
                self._ignore.maybe_commit_midway()
                results.append(result)
        return results

    def _should_visit(self, location: AnimeDir | SubtitleFile) -> bool:
        """
        The page is visited if it was modified recently enough.
        On full sync, visit and download everything.
        """
        if self._full_sync:
            return True
        return location.mod_timestamp >= (self._now - self._config.skip_older)

    async def crawl_page(self, client: httpx.AsyncClient, anime_dir: AnimeDir) -> PageCrawlResult:
        try:
            r = await client.get(anime_dir.url)
        except Exception as e:
            raise DownloadError(anime_dir.url) from e

        return PageCrawlResult(
            visited_dir=anime_dir,
            found_dirs=[*filter(self._should_visit, find_all_subtitle_dirs(r.text))],
            found_files=[*filter(self._should_visit, find_all_subtitle_files(r.text))],
        )

    async def find_subs_all(self, client: httpx.AsyncClient, to_visit: set[AnimeDir]) -> FetchResult:
        results = FetchResult.new()
        for fut in asyncio.as_completed([self.crawl_page(client, page) for page in to_visit]):
            try:
                page_visit: PageCrawlResult = await fut
            except DownloadError as ex:
                print(f"got {ex.what} while trying to download {ex.url}")
            else:
                print(page_visit)
                downloads = await self.download_subs(client, page_visit.found_files)
                results.update(page_visit, downloads)
        return results

    async def sync_all(self) -> None:
        async with get_http_client(self._config) as client:
            state = FetchState.new(self._config.download_root)
            while state.has_unvisited():
                task: FetchResult = await self.find_subs_all(client, state.to_visit)
                print(task)
                state.balance(task)
        self._ignore.commit()
