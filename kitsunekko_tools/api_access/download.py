# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import asyncio
import collections
import dataclasses
import datetime
import enum
import typing
from collections.abc import Coroutine

import httpx

from kitsunekko_tools.api_access.file_entry import iter_directory_files, ApiFileEntry
from kitsunekko_tools.api_access.rate_limit import RateLimit
from kitsunekko_tools.api_access.root_directory import iter_catalog_directories, ApiDirectoryEntry
from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import get_config, KitsuConfig
from kitsunekko_tools.file_downloader import (
    KitsuConnectionError,
    KitsuSubtitleDownloader,
    KitsuSubtitleDownload,
    SubtitleFileUrl,
)
from kitsunekko_tools.ignore import IgnoreList


@enum.unique
class SearchResponseCode(enum.Enum):
    """
    Status codes that are expected from the API when searching the catalog.
    """

    successful = 200
    unauthenticated = 401
    rate_limit_exceeded = 429


@enum.unique
class FilesResponseCode(enum.Enum):
    """
    Status codes that are expected from the API when requesting a list of files.
    """

    successful = 200
    invalid_id_given = 400
    entry_not_found = 404
    unauthenticated = 401
    rate_limit_exceeded = 429


def get_http_api_client(config: KitsuConfig) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        proxies=config.proxy,
        headers=typing.cast(typing.Mapping[str, str], config.api_headers()),
        timeout=config.timeout,
        follow_redirects=False,
    )


@dataclasses.dataclass(frozen=True)
class ApiBadStatusError(KitsuException):
    status: SearchResponseCode | FilesResponseCode

    @property
    def what(self) -> str:
        return f"{self.status.value} ({self.status.name.replace('_', ' ')})"

    def __str__(self) -> str:
        return f"got response {self.what}."


@dataclasses.dataclass(frozen=True)
class ApiRateLimitedError(ApiBadStatusError):
    rate_limit: RateLimit


def make_payload(
    config: KitsuConfig, directory: ApiDirectoryEntry, found_files: typing.Iterable[ApiFileEntry]
) -> typing.Sequence[KitsuSubtitleDownload]:
    return [
        KitsuSubtitleDownload(
            url=SubtitleFileUrl(file.url),
            file_path=(config.destination / directory.name / file.name),
        )
        for file in found_files
    ]


class ApiSyncClient:
    _config: KitsuConfig
    _ignore: IgnoreList
    _now: datetime.datetime
    _full_sync: bool
    _is_anime: bool
    _rate_limit: None | RateLimit

    def __init__(self, config: KitsuConfig, full_sync: bool = False, is_anime: bool = True):
        self._config = config
        self._config.raise_for_destination()
        self._ignore = IgnoreList(self._config)
        self._downloader = KitsuSubtitleDownloader(self._config, self._ignore)
        self._now = datetime.datetime.now()
        self._full_sync = full_sync
        self._is_anime = is_anime
        self._rate_limit = None
        self._tasks: collections.deque[Coroutine] = collections.deque()

    def _construct_search_args_str(self) -> str:
        args: dict[str, object] = {"anime": self._is_anime}
        if not self._full_sync:
            args["after"] = (self._now - self._config.skip_older).strftime("%s")
        return "&".join(f"{key}={str(value).lower()}" for key, value in args.items())

    def get_search_url(self) -> str:
        return f"{self._config.api_url}/entries/search?{self._construct_search_args_str()}"

    def get_dir_listing_url(self, directory: ApiDirectoryEntry) -> str:
        return f"{self._config.api_url}/entries/{directory.entry_id}/files"

    async def _run_tasks(self) -> None:
        while self._tasks:
            if not self._rate_limit or self._rate_limit.remaining > 0:
                print(f"Running task. Rate limit status: {self._rate_limit}")
                try:
                    await self._tasks.popleft()
                except (KitsuConnectionError, ApiBadStatusError) as e:
                    print(e)
            else:
                print(
                    f"Rate limited. Rate limit status: {self._rate_limit}. "
                    f"Sleeping for {self._rate_limit.time_left()} seconds."
                )
                await self._rate_limit.sleep()

    def _handle_search_status(self, r: httpx.Response):
        rate_limit = self._rate_limit = RateLimit.from_headers(r.headers)
        match status := SearchResponseCode(r.status_code):
            case SearchResponseCode.successful:
                return
            case SearchResponseCode.unauthenticated:
                raise ApiBadStatusError(status)
            case SearchResponseCode.rate_limit_exceeded:
                raise ApiRateLimitedError(status, rate_limit)

    def _handle_directory_status(self, r: httpx.Response):
        rate_limit = self._rate_limit = RateLimit.from_headers(r.headers)
        match status := FilesResponseCode(r.status_code):
            case FilesResponseCode.successful:
                return
            case FilesResponseCode.rate_limit_exceeded:
                raise ApiRateLimitedError(status, rate_limit)
            case _:
                raise ApiBadStatusError(status)

    async def _get_directory_files(self, client: httpx.AsyncClient, details_url: str) -> typing.Sequence[ApiFileEntry]:
        try:
            r = await client.get(details_url)
        except Exception as e:
            raise KitsuConnectionError(details_url) from e
        else:
            self._handle_directory_status(r)
            return [*iter_directory_files(r.json())]

    async def _visit_directory(self, client: httpx.AsyncClient, directory: ApiDirectoryEntry) -> None:
        try:
            files = await self._get_directory_files(client, self.get_dir_listing_url(directory))
        except ApiRateLimitedError as e:
            self._tasks.append(self._visit_directory(client, directory))
            print(f"Rate limited. Sleeping for {e.rate_limit.time_left()}.")
            await e.rate_limit.sleep()
            raise
        print(f"visited directory '{directory.name}'. found {len(files)} files.")
        results = await self._downloader.download_subs(
            client=client,
            to_download=make_payload(self._config, directory, files),
        )
        print(
            f"in directory '{directory.name}': "
            f"saved {results.num_saved()} files. "
            f"failed {results.num_failed()} files."
        )

    async def _search_catalog(self, client: httpx.AsyncClient, search_url: str) -> None:
        try:
            r = await client.get(search_url)
        except Exception as e:
            raise KitsuConnectionError(search_url) from e
        try:
            self._handle_search_status(r)
        except ApiRateLimitedError as e:
            self._tasks.append(self._search_catalog(client, search_url))
            print(f"Rate limited. Sleeping for {e.rate_limit.time_left()}.")
            await e.rate_limit.sleep()
            raise
        for directory in iter_catalog_directories(r.json()):
            try:
                await self._visit_directory(client, directory)
            except (KitsuConnectionError, ApiBadStatusError) as e:
                print(e)

    async def sync(self):
        async with get_http_api_client(self._config) as client:
            self._tasks.append(self._search_catalog(client, self.get_search_url()))
            await self._run_tasks()


async def main():
    config = get_config().data
    client = ApiSyncClient(config, is_anime=True, full_sync=False)
    print(client.get_search_url())
    await client.sync()


if __name__ == "__main__":
    asyncio.run(main())
