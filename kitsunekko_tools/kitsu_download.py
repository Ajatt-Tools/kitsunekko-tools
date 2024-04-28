# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import asyncio
import dataclasses
import enum
import os.path
import pathlib
import re
import typing
from datetime import datetime
from urllib.parse import unquote

import httpx

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import get_config, KitsuConfig
from kitsunekko_tools.consts import *
from kitsunekko_tools.ignore import IgnoreList


def is_file_non_empty(file_path: pathlib.Path) -> bool:
    """
    Returns True if file exists and is not empty.
    """
    return file_path.is_file() and file_path.stat().st_size > 0


@dataclasses.dataclass(frozen=True)
class AnimeSubtitleUrl:
    url: str
    title: str

    @property
    def file_name(self) -> str:
        return unquote(self.url).split("/")[-1]


AnimeDirUrl = typing.NewType("AnimeDirUrl", str)


class PageCrawlResult(typing.NamedTuple):
    visited_dir: AnimeDirUrl
    found_dirs: list[AnimeDirUrl]
    found_files: list[AnimeSubtitleUrl]


@dataclasses.dataclass(frozen=True)
class FetchResult:
    to_visit: set[AnimeDirUrl]
    to_download: set[AnimeSubtitleUrl]
    visited: set[AnimeDirUrl]

    @classmethod
    def new(cls):
        return cls(to_visit=set(), to_download=set(), visited=set())

    def update(self, dir_result: PageCrawlResult):
        self.to_visit.update(dir_result.found_dirs)
        self.to_download.update(dir_result.found_files)
        self.visited.add(dir_result.visited_dir)


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
    file_path: pathlib.Path

    def __repr__(self):
        return f"{self.reason}: {self.file_path}"


@dataclasses.dataclass(frozen=True)
class FetchState:
    to_visit: set[AnimeDirUrl]
    visited: set[AnimeDirUrl]

    @classmethod
    def new(cls, download_root: AnimeDirUrl) -> typing.Self:
        return cls(
            to_visit={
                download_root,
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


def find_all_subtitle_dir_urls(html_text: str) -> list[str]:
    return re.findall(r'(?<="/)dirlist.php\?[^"\']+(?=")', html_text)


def find_all_subtitle_file_urls(html_text: str) -> list[str]:
    return re.findall(r'(?<=href=")subtitles/[^"\']+\.(?:zip|rar|ass|srt)(?=")', html_text)


class AnimeSubtitleFile:
    def __init__(self, remote: AnimeSubtitleUrl, root_dir_path: pathlib.Path):
        self.dir_path = root_dir_path / remote.title
        self.file_path = self.dir_path / remote.file_name
        self.remote_url = remote.url

    def ensure_subtitle_dir(self) -> None:
        """
        Create directory to store the subtitle file.
        """
        return self.dir_path.mkdir(exist_ok=True)

    def is_already_downloaded(self) -> bool:
        return is_file_non_empty(self.file_path)


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

    def __init__(self):
        self._config = get_config().data
        self._ignore = IgnoreList(self._config)
        self._config.raise_for_destination()

    async def download_sub(self, client: httpx.AsyncClient, subtitle: AnimeSubtitleFile) -> DownloadResult:
        subtitle.ensure_subtitle_dir()

        if subtitle.is_already_downloaded():
            return DownloadResult(DownloadStatus.already_exists, subtitle.file_path)

        if self._ignore.is_matching(subtitle.file_path):
            return DownloadResult(DownloadStatus.explicitly_ignored, subtitle.file_path)

        try:
            r = await client.get(subtitle.remote_url)
        except Exception as e:
            raise DownloadError(subtitle.remote_url) from e
        if r.status_code != httpx.codes.OK:
            return DownloadResult(DownloadStatus.download_failed, subtitle.file_path)
        with open(subtitle.file_path, "wb") as f:
            f.write(r.content)
        return DownloadResult(DownloadStatus.saved, subtitle.file_path)

    async def download_subs(self, client: httpx.AsyncClient, to_download: typing.Iterable[AnimeSubtitleFile]) -> None:
        for fut in asyncio.as_completed(tuple(self.download_sub(client, subtitle) for subtitle in to_download)):
            try:
                print(await fut)
            except DownloadError as e:
                print(f"got {e.what} while trying to download {e.url}")

    async def crawl_page(self, client: httpx.AsyncClient, url: AnimeDirUrl) -> PageCrawlResult:
        try:
            r = await client.get(url)
        except Exception as e:
            raise DownloadError(url) from e

        return PageCrawlResult(
            visited_dir=url,
            found_dirs=[
                AnimeDirUrl(f"{KITSUNEKKO_DOMAIN_URL}/{anime_dir}") for anime_dir in find_all_subtitle_dir_urls(r.text)
            ],
            found_files=[
                AnimeSubtitleUrl(f"{KITSUNEKKO_DOMAIN_URL}/{subtitle}", get_anime_title(r.text))
                for subtitle in find_all_subtitle_file_urls(r.text)
            ],
        )

    async def find_subs_all(self, client: httpx.AsyncClient, to_visit: set[AnimeDirUrl]) -> FetchResult:
        results = FetchResult.new()
        for fut in asyncio.as_completed([self.crawl_page(client, page) for page in to_visit]):
            try:
                result = await fut
            except DownloadError as e:
                print(f"got {e.what} while trying to download {e.url}")
            else:
                print(f"visited page {result.visited_dir}, found {len(result.found_files)} files.")
                results.update(result)
        return results

    async def sync_all(self) -> None:
        async with get_http_client(self._config) as client:
            state = FetchState.new(AnimeDirUrl(self._config.download_root))
            while state.has_unvisited():
                task: FetchResult = await self.find_subs_all(client, state.to_visit)
                print(f"visited {len(task.visited)} pages, found {len(task.to_download)} files.")
                await self.download_subs(
                    client,
                    (AnimeSubtitleFile(url, self._config.destination) for url in task.to_download),
                )
                state.balance(task)