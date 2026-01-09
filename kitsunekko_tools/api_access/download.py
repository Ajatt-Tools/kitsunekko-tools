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

from kitsunekko_tools.api_access.directory_entry import KitsuDirectoryEntry
from kitsunekko_tools.api_access.file_entry import ApiFileEntry, iter_directory_files
from kitsunekko_tools.api_access.rate_limit import RateLimit
from kitsunekko_tools.api_access.root_directory import (
    ApiDirectoryEntry,
    iter_catalog_directories,
)
from kitsunekko_tools.common import SKIP_FILES, KitsuException, datetime_now_utc
from kitsunekko_tools.config import KitsuConfig, get_config
from kitsunekko_tools.consts import TRASH_DIR_NAME
from kitsunekko_tools.download import ClientBase
from kitsunekko_tools.file_downloader import (
    DownloadSubtitlesList,
    KitsuConnectionError,
    KitsuSubtitleDownload,
    KitsuSubtitleDownloader,
    SubtitleFileUrl,
)
from kitsunekko_tools.ignore import IgnoreTSVForDir, get_ignore_file_path_on_disk
from kitsunekko_tools.website.templates import date_allposts_post_filter


@enum.unique
class ApiResponseCode(enum.Enum):
    """
    Status codes that are expected from the API.
    """

    successful = 200
    invalid_id_given = 400
    unauthenticated = 401
    entry_not_found = 404
    rate_limit_exceeded = 429


def get_http_api_client(config: KitsuConfig) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        proxy=config.proxy,
        headers=typing.cast(typing.Mapping[str, str], config.api_headers()),
        timeout=config.timeout,
        follow_redirects=False,
    )


@dataclasses.dataclass(frozen=True)
class ApiBadStatusError(KitsuException):
    status: ApiResponseCode

    @property
    def what(self) -> str:
        return f"{self.status.value} ({self.status.name.replace('_', ' ')})"

    def __str__(self) -> str:
        return f"got response {self.what}."


@dataclasses.dataclass(frozen=True)
class ApiRateLimitedError(ApiBadStatusError):
    rate_limit: RateLimit

    def __str__(self) -> str:
        return f"rate limited. remaining time {self.rate_limit.reset_after}."


def api_make_payload(
    directory: KitsuDirectoryEntry, found_files: typing.Iterable[ApiFileEntry]
) -> DownloadSubtitlesList:
    return DownloadSubtitlesList(
        to_download=[
            KitsuSubtitleDownload(
                url=SubtitleFileUrl(file.url),
                file_path=(directory.dir_path / file.name),
                entry=directory,
                last_modified_on_remote=file.last_modified,
            )
            for file in found_files
        ],
        ignore_list=IgnoreTSVForDir(ignore_filepath=get_ignore_file_path_on_disk(directory.dir_path)),
    )


def handle_response_status(response: httpx.Response):
    match status := ApiResponseCode(response.status_code):
        case ApiResponseCode.successful:
            return
        case ApiResponseCode.rate_limit_exceeded:
            raise ApiRateLimitedError(status, RateLimit.from_headers(response.headers))
        case _:
            raise ApiBadStatusError(status)


async def get_directory_files(client: httpx.AsyncClient, details_url: str) -> typing.Sequence[ApiFileEntry]:
    try:
        r = await client.get(details_url)
    except Exception as e:
        raise KitsuConnectionError(details_url) from e
    else:
        handle_response_status(r)
        return [*iter_directory_files(r.json())]


async def get_catalog_dirs(client: httpx.AsyncClient, search_url: str) -> typing.Sequence[ApiDirectoryEntry]:
    try:
        r = await client.get(search_url)
    except Exception as e:
        raise KitsuConnectionError(search_url) from e
    else:
        handle_response_status(r)
        # Newest entries first
        return sorted(iter_catalog_directories(r.json()), key=lambda entry: entry.last_modified, reverse=True)


def trash_files_missing_on_remote(directory: KitsuDirectoryEntry, remote_files: typing.Sequence[ApiFileEntry]) -> None:
    all_names = {
        entry.name for entry in directory.dir_path.iterdir() if entry.is_file() and entry.name not in SKIP_FILES
    }
    keep_names = {file.name for file in remote_files}
    move_names = all_names - keep_names
    if not move_names:
        return
    print(f"in dir {directory.dir_path.name}: moving {len(move_names)} files to '{TRASH_DIR_NAME}'")
    directory.dir_path.joinpath(TRASH_DIR_NAME).mkdir(exist_ok=True)
    for file_name in move_names:
        old_path = directory.dir_path / file_name
        new_path = directory.dir_path / TRASH_DIR_NAME / file_name
        old_path.rename(new_path)


class ApiSyncClient(ClientBase):
    _config: KitsuConfig
    _downloader: KitsuSubtitleDownloader
    _now: datetime.datetime
    _full_sync: bool
    _ignore_dir_mod_times: bool
    _tasks: collections.deque[Coroutine]

    def __init__(self, config: KitsuConfig, full_sync: bool = False, ignore_dir_mod_times: bool = False) -> None:
        super().__init__()
        self._config = config
        self._config.raise_for_destination()
        self._downloader = KitsuSubtitleDownloader(self._config)
        self._now = datetime_now_utc()
        self._full_sync = full_sync
        self._ignore_dir_mod_times = ignore_dir_mod_times
        self._tasks = collections.deque()

    def _construct_search_args_str(self, is_anime: bool) -> str:
        args: dict[str, object] = {"anime": is_anime}
        if not self._full_sync:
            args["after"] = (self._now - self._config.skip_older).strftime("%s")
        return "&".join(f"{key}={str(value).lower()}" for key, value in args.items())

    def get_search_url(self, is_anime: bool) -> str:
        return f"{self._config.api_url}/api/entries/search?{self._construct_search_args_str(is_anime)}"

    async def _run_tasks(self) -> None:
        while self._tasks:
            print(f"Running task.")
            try:
                await self._tasks.popleft()
            except (KitsuConnectionError, ApiBadStatusError) as e:
                print(e)

    async def _visit_directory(self, client: httpx.AsyncClient, directory: KitsuDirectoryEntry) -> None:
        if not self._ignore_dir_mod_times and not directory.should_visit_directory():
            print(f"skipped directory that has been visited recently: '{directory.name}'")
            return
        try:
            files = await get_directory_files(client, directory.dir_listing_url)
        except ApiRateLimitedError as e:
            self._tasks.append(self._visit_directory(client, directory))
            print(e)
            await e.rate_limit.sleep()
            return
        print(
            f"visited directory: '{directory.name}'. "
            f"found: {len(files)} files. "
            f"mod time: {date_allposts_post_filter(directory.remote_dir.last_modified)}."
        )
        results = await self._downloader.download_subs(
            client=client,
            entry=api_make_payload(directory, files),
        )
        print(
            f"in directory '{directory.name}': "
            f"saved {results.num_saved()} files. "
            f"failed {results.num_failed()} files."
        )
        if results.num_failed() == 0:
            directory.ensure_exists()
            directory.write_meta()
            trash_files_missing_on_remote(directory, files)

    async def _search_catalog(self, client: httpx.AsyncClient, search_url: str) -> None:
        try:
            directories = await get_catalog_dirs(client, search_url)
        except ApiRateLimitedError as e:
            self._tasks.append(self._search_catalog(client, search_url))
            print(e)
            await e.rate_limit.sleep()
            return
        print(f"visited root catalog. found {len(directories)} directories.")
        for directory in directories:
            try:
                await self._visit_directory(client, KitsuDirectoryEntry.from_remote(directory, self._config))
            except (KitsuConnectionError, ApiBadStatusError) as e:
                print(e)

    async def sync_all(self) -> None:
        print(f"Sync start ({'full' if self._full_sync else 'normal'}).")
        async with get_http_api_client(self._config) as client:
            self._tasks.append(self._search_catalog(client, self.get_search_url(is_anime=True)))
            self._tasks.append(self._search_catalog(client, self.get_search_url(is_anime=False)))
            await self._run_tasks()
        print("Finished.")


async def main():
    config = get_config().data
    client = ApiSyncClient(config, full_sync=False)
    await client.sync_all()


if __name__ == "__main__":
    asyncio.run(main())
