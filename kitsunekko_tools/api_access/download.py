# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import asyncio
import collections
import dataclasses
import datetime
import enum
import pathlib
import typing
from collections.abc import Coroutine

import httpx

from kitsunekko_tools.api_access.file_entry import ApiFileEntry, iter_directory_files
from kitsunekko_tools.api_access.rate_limit import RateLimit
from kitsunekko_tools.api_access.root_directory import (
    ApiDirectoryEntry,
    KitsuDirectoryMeta,
    iter_catalog_directories,
)
from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import KitsuConfig, get_config
from kitsunekko_tools.consts import INFO_FILENAME, TRASH_DIR_NAME
from kitsunekko_tools.download import ClientBase, ClientType
from kitsunekko_tools.file_downloader import (
    KitsuConnectionError,
    KitsuSubtitleDownload,
    KitsuSubtitleDownloader,
    SubtitleFileUrl,
)
from kitsunekko_tools.ignore import IgnoreList
from kitsunekko_tools.sanitize import SKIP_FILES


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


def get_meta_file_path(remote_dir: ApiDirectoryEntry, config: KitsuConfig) -> pathlib.Path:
    return pathlib.Path(config.destination / remote_dir.name / INFO_FILENAME)


def read_meta_file(meta_file_path: pathlib.Path) -> KitsuDirectoryMeta | None:
    try:
        with open(meta_file_path, encoding="utf-8") as f:
            assert meta_file_path.parent.is_dir(), "parent directory must exist."
            return KitsuDirectoryMeta.from_local_file(f, dir_path=meta_file_path.parent)
    except FileNotFoundError:
        return None


@dataclasses.dataclass(frozen=True)
class KitsuDirectoryEntry:
    remote_dir: ApiDirectoryEntry
    meta_file_path: pathlib.Path
    dir_listing_url: str
    local_state: KitsuDirectoryMeta | None

    @property
    def dir_path(self) -> pathlib.Path:
        return self.meta_file_path.parent

    @property
    def name(self) -> str:
        return self.remote_dir.name

    @classmethod
    def from_remote(cls, remote_dir: ApiDirectoryEntry, config: KitsuConfig):
        meta_file_path = get_meta_file_path(remote_dir, config)

        return cls(
            remote_dir=remote_dir,
            meta_file_path=meta_file_path,
            dir_listing_url=f"{config.api_url}/api/entries/{remote_dir.entry_id}/files",
            local_state=read_meta_file(meta_file_path),
        )

    def should_visit_directory(self) -> bool:
        """
        Visit the directory if the remote is more recent.
        """
        if not self.local_state:
            return True
        return self.remote_dir.last_modified > self.local_state.last_modified

    def write_meta(self) -> None:
        with open(self.meta_file_path, "w", encoding="utf-8") as of:
            self.remote_dir.write_to_file(of)

    def ensure_exists(self) -> None:
        self.meta_file_path.parent.mkdir(exist_ok=True)


def make_payload(
    directory: KitsuDirectoryEntry, found_files: typing.Iterable[ApiFileEntry]
) -> typing.Sequence[KitsuSubtitleDownload]:
    return [
        KitsuSubtitleDownload(
            url=SubtitleFileUrl(file.url),
            file_path=(directory.dir_path / file.name),
        )
        for file in found_files
    ]


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
        return [*iter_catalog_directories(r.json())]


def trash_files_missing_on_remote(directory: KitsuDirectoryEntry, remote_files: typing.Sequence[ApiFileEntry]) -> None:
    all_names = {
        entry.name for entry in directory.dir_path.iterdir() if entry.is_file() and entry.name not in SKIP_FILES
    }
    keep_names = {file.name for file in remote_files}
    move_names = all_names - keep_names
    if not move_names:
        return
    print(f"in dir {directory.remote_dir.name}: moving {len(move_names)} files to '{TRASH_DIR_NAME}'")
    for file_name in move_names:
        old_path = directory.dir_path / file_name
        new_path = directory.dir_path / TRASH_DIR_NAME / file_name
        new_path.parent.mkdir(exist_ok=True)
        old_path.rename(new_path)


class ApiSyncClient(ClientBase, client_type=ClientType.api):
    _config: KitsuConfig
    _ignore: IgnoreList
    _downloader: KitsuSubtitleDownloader
    _now: datetime.datetime
    _full_sync: bool
    _tasks: collections.deque[Coroutine]

    def __init__(self, client_type: ClientType, config: KitsuConfig, full_sync: bool = False) -> None:
        super().__init__(client_type, config, full_sync)
        self._config = config
        self._config.raise_for_destination()
        self._ignore = IgnoreList(self._config)
        self._downloader = KitsuSubtitleDownloader(self._config, self._ignore)
        self._now = datetime.datetime.now()
        self._full_sync = full_sync
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
        if not directory.should_visit_directory():
            print(f"skipped directory that has been visited recently: '{directory.name}'")
            return
        try:
            files = await get_directory_files(client, directory.dir_listing_url)
        except ApiRateLimitedError as e:
            self._tasks.append(self._visit_directory(client, directory))
            print(e)
            await e.rate_limit.sleep()
            return
        print(f"visited directory '{directory.name}'. found {len(files)} files.")
        results = await self._downloader.download_subs(
            client=client,
            to_download=make_payload(directory, files),
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
