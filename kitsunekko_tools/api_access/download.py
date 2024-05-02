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

from kitsunekko_tools.api_access.directory import iter_catalog_directories, ApiDirectoryEntry
from kitsunekko_tools.api_access.rate_limit import RateLimit
from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import get_config, KitsuConfig
from kitsunekko_tools.ignore import IgnoreList


@enum.unique
class SearchResponseCode(enum.Enum):
    """
    Status codes that are expected from the API.
    """
    successful = 200
    unauthenticated = 401
    rate_limit_exceeded = 429


def get_http_api_client(config: KitsuConfig) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        proxies=config.proxy,
        headers=config.api_headers(),
        timeout=config.timeout,
        follow_redirects=False,
    )


@dataclasses.dataclass(frozen=True)
class ApiConnectionError(KitsuException):
    """
    Failed to connect. Raised from another exception.
    """
    url: str

    @property
    def what(self) -> str:
        return type(self.__cause__).__name__

    def __str__(self) -> str:
        return f"got {self.what} while trying to download {self.url}"


@dataclasses.dataclass(frozen=True)
class ApiBadStatusError(KitsuException):
    status: SearchResponseCode

    @property
    def what(self) -> str:
        return f"{self.status.value} ({self.status.name.replace('_', ' ')})"

    def __str__(self) -> str:
        return f"got response {self.what}."


@dataclasses.dataclass(frozen=True)
class ApiRateLimitedError(ApiBadStatusError):
    pass


class LocalDirectoryEntry(typing.NamedTuple):
    remote: ApiDirectoryEntry  # remote URL
    dir_path: pathlib.Path  # path to the directory on the hard drive

    @classmethod
    def new(cls, remote: ApiDirectoryEntry, config: KitsuConfig):
        return cls(
            remote=remote,
            dir_path=(config.destination / remote.name),
        )

    def ensure_subtitle_dir(self) -> None:
        """
        Create directory to store the subtitle files.
        """
        return self.dir_path.mkdir(exist_ok=True)

    def is_already_downloaded(self) -> bool:
        return is_file_non_empty(self.file_path)


class ApiSyncClient:
    _config: KitsuConfig
    _ignore: IgnoreList
    _now: datetime
    _full_sync: bool
    _is_anime: bool
    _rate_limit: None | RateLimit

    def __init__(self, config: KitsuConfig, full_sync: bool = False, is_anime: bool = True):
        self._config = config
        self._config.raise_for_destination()
        self._ignore = IgnoreList(self._config)
        self._now = datetime.datetime.now()
        self._full_sync = full_sync
        self._is_anime = is_anime
        self._rate_limit = None
        self._tasks: collections.deque[Coroutine] = collections.deque()

    def _construct_search_args_str(self) -> str:
        args = {"anime": self._is_anime}
        if not self._full_sync:
            args["after"] = (self._now - self._config.skip_older).strftime("%s")
        return "&".join(f"{key}={str(value).lower()}" for key, value in args.items())

    def get_search_url(self) -> str:
        return f"{self._config.api_url}/entries/search?{self._construct_search_args_str()}"

    async def _run_tasks(self) -> None:
        while self._tasks:
            if not self._rate_limit or self._rate_limit.remaining > 0:
                print(f"Running task. Rate limit status: {self._rate_limit}")
                try:
                    await self._tasks.popleft()
                except (ApiConnectionError, ApiBadStatusError) as e:
                    print(e)
            else:
                print(
                    f"Rate limited. Rate limit status: {self._rate_limit}. "
                    f"Sleeping for {self._rate_limit.reset_after} seconds."
                )
                await asyncio.sleep(self._rate_limit.reset_after + 0.1)

    def _handle_status(self, r: httpx.Response):
        self._rate_limit = RateLimit.from_headers(r.headers)
        match status := SearchResponseCode(r.status_code):
            case SearchResponseCode.successful:
                return
            case SearchResponseCode.unauthenticated:
                raise ApiBadStatusError(status)
            case SearchResponseCode.rate_limit_exceeded:
                raise ApiRateLimitedError(status)

    async def _search_catalog(self, client: httpx.AsyncClient, search_url: str) -> None:
        try:
            r = await client.get(search_url)
        except Exception as e:
            raise ApiConnectionError(search_url) from e
        try:
            self._handle_status(r)
        except ApiRateLimitedError:
            self._tasks.append(self._search_catalog(client, search_url))
            raise
        for directory in iter_catalog_directories(r.json()):
            print(directory)

    async def sync(self):
        async with get_http_api_client(self._config) as client:
            self._tasks.append(self._search_catalog(client, self.get_search_url()))
            await self._run_tasks()


async def main():
    config = get_config().data
    client = ApiSyncClient(config, is_anime=False)
    print(client.get_search_url())
    await client.sync()


if __name__ == "__main__":
    asyncio.run(main())
