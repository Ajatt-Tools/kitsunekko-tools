# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import asyncio
import datetime
import typing
from collections.abc import Sequence

import httpx

from kitsunekko_tools.common import KitsuError
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import IGNORE_FILENAME
from kitsunekko_tools.download import ClientBase, ClientType
from kitsunekko_tools.file_downloader import (
    DownloadSubtitlesList,
    KitsuConnectionError,
    KitsuDownloadResults,
    KitsuSubtitleDownload,
    KitsuSubtitleDownloader,
    SubtitleFileUrl,
)
from kitsunekko_tools.ignore import IgnoreListForDir
from kitsunekko_tools.scrapper.parse import (
    find_all_subtitle_dirs,
    find_all_subtitle_files,
)
from kitsunekko_tools.scrapper.types import AnimeDir, SubtitleFile


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


class FetchResult(typing.NamedTuple):
    to_visit: set[AnimeDir]
    to_download: set[SubtitleFile]
    visited: set[AnimeDir]
    results: KitsuDownloadResults

    @classmethod
    def new(cls):
        return cls(
            to_visit=set(),
            to_download=set(),
            visited=set(),
            results=KitsuDownloadResults(),
        )

    def update(self, dir_result: PageCrawlResult, downloads: KitsuDownloadResults | None):
        self.to_visit.update(dir_result.found_dirs)
        self.to_download.update(dir_result.found_files)
        self.visited.add(dir_result.visited_dir)
        if downloads:
            self.results.update(downloads)

    def __str__(self) -> str:
        return str(
            f"visited {len(self.visited)} pages. "
            f"saved {self.results.num_saved()} files. "
            f"failed {self.results.num_failed()} files."
        )


class FetchState(typing.NamedTuple):
    to_visit: set[AnimeDir]
    visited: set[AnimeDir]

    @classmethod
    def new(cls, download_root_url: str) -> typing.Self:
        return cls(
            to_visit={
                AnimeDir(download_root_url, "subtitles", datetime.datetime.now(tz=datetime.UTC)),
            },
            visited=set(),
        )

    def balance(self, prev_result: FetchResult) -> None:
        self.visited.update(self.to_visit)
        self.to_visit.clear()
        self.to_visit.update(prev_result.to_visit - self.visited)

    def has_unvisited(self) -> bool:
        return len(self.to_visit) > 0


def get_http_client(config: KitsuConfig) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        proxy=config.proxy,
        headers=config.headers,
        timeout=config.timeout,
        follow_redirects=False,
    )


def get_show_name(found_files: Sequence[SubtitleFile]) -> str:
    names = {file.show_name for file in found_files}
    if len(names) != 1:
        raise KitsuError(f"more than one show name found: {names}")
    return names.pop()


def scrapper_make_payload(config: KitsuConfig, found_files: Sequence[SubtitleFile]) -> DownloadSubtitlesList:
    show_name = get_show_name(found_files)
    return DownloadSubtitlesList(
        to_download=[
            KitsuSubtitleDownload(
                url=SubtitleFileUrl(file.url),
                file_path=(config.destination / show_name / file.file_name),
                last_modified_on_remote=file.mod_timestamp,
            )
            for file in found_files
        ],
        ignore_list=IgnoreListForDir(ignore_filepath=config.destination.joinpath(show_name, IGNORE_FILENAME)),
    )


class KitsuScrapper(ClientBase):
    _config: KitsuConfig
    _downloader: KitsuSubtitleDownloader
    _now: datetime.datetime
    _full_sync: bool

    def __init__(self, config: KitsuConfig, full_sync: bool = False) -> None:
        super().__init__()
        self._config = config
        self._config.raise_for_destination()
        self._downloader = KitsuSubtitleDownloader(self._config)
        self._now = datetime.datetime.now(tz=datetime.UTC)
        self._full_sync = full_sync

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
            raise KitsuConnectionError(anime_dir.url) from e

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
            except KitsuConnectionError as ex:
                print(ex)
            else:
                print(page_visit)
                if page_visit.found_files:
                    downloads = await self._downloader.download_subs(
                        client=client,
                        entry=scrapper_make_payload(self._config, page_visit.found_files),
                    )
                else:
                    downloads = None
                results.update(page_visit, downloads)
                # TODO write .kitsuinfo.json
        return results

    async def sync_all(self) -> None:
        async with get_http_client(self._config) as client:
            state = FetchState.new(self._config.download_root)
            while state.has_unvisited():
                task: FetchResult = await self.find_subs_all(client, state.to_visit)
                print(task)
                state.balance(task)
