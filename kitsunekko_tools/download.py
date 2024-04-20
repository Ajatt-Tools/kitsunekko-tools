# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import asyncio
import dataclasses
import os.path
import re
import typing
from collections.abc import Collection
from datetime import datetime
from urllib.parse import unquote

import httpx

from kitsunekko_tools.config import get_config
from kitsunekko_tools.consts import *
from kitsunekko_tools.ignore import IgnoreList


def file_exists(file_path: str) -> bool:
    return os.path.isfile(file_path) and os.stat(file_path).st_size > 0


@dataclasses.dataclass(frozen=True)
class AnimeSubtitleUrl:
    url: str
    title: str

    @property
    def file_name(self) -> str:
        return os.path.basename(unquote(self.url))


@dataclasses.dataclass(frozen=True)
class FetchResult:
    to_visit: set[str]
    to_download: set[AnimeSubtitleUrl]

    @classmethod
    def new(cls):
        return cls(to_visit=set(), to_download=set())

    def update(self, other: "FetchResult"):
        self.to_visit.update(other.to_visit)
        self.to_download.update(other.to_download)


@dataclasses.dataclass(frozen=True)
class DownloadResult:
    reason: str
    file_path: str

    def __repr__(self):
        return f"{self.reason}: {self.file_path}"


@dataclasses.dataclass(frozen=True)
class FetchState:
    to_visit: set[str]
    visited: set[str]

    @classmethod
    def new(cls, download_root: str) -> typing.Self:
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
class DownloadError(Exception):
    url: str

    @property
    def errname(self) -> str:
        return type(self.__cause__).__name__


def get_anime_title(page_text: str) -> str:
    title = re.search(r"<title>([^<>]+)</title>", page_text, flags=re.IGNORECASE | re.MULTILINE).group(1)
    title = title.replace(" - Japanese subtitles - kitsunekko.net", "").replace("/", " ").replace("\\", " ")
    return title.strip()


def find_all_subtitle_dir_urls(html_text: str) -> list[str]:
    return re.findall(r'(?<="/)dirlist.php\?[^"\']+(?=")', html_text)


def find_all_subtitle_file_urls(html_text: str) -> list[str]:
    return re.findall(r'(?<=href=")subtitles/[^"\']+\.(?:zip|rar|ass|srt)(?=")', html_text)


async def crawl_page(client: httpx.AsyncClient, url: str) -> FetchResult:
    try:
        r = await client.get(url)
    except Exception as e:
        raise DownloadError(url) from e

    return FetchResult(
        to_visit={f"{KITSUNEKKO_DOMAIN_URL}/{anime_dir}" for anime_dir in find_all_subtitle_dir_urls(r.text)},
        to_download={
            AnimeSubtitleUrl(f"{KITSUNEKKO_DOMAIN_URL}/{subtitle}", get_anime_title(r.text))
            for subtitle in find_all_subtitle_file_urls(r.text)
        },
    )


async def find_subs_all(client: httpx.AsyncClient, to_visit: set[str]) -> FetchResult:
    result = FetchResult.new()
    for fut in asyncio.as_completed([crawl_page(client, page) for page in to_visit]):
        try:
            result.update(await fut)
        except DownloadError as e:
            print(f"got {e.errname} while trying to download {e.url}")
    return result


class Sync:
    def __init__(self):
        self._config = get_config().data
        self._ignore = IgnoreList(self._config)

    async def download_sub(self, client: httpx.AsyncClient, subtitle: AnimeSubtitleUrl) -> DownloadResult:
        if not os.path.isdir(dir_path := os.path.join(self._config.destination, subtitle.title)):
            os.mkdir(dir_path)
        if file_exists(file_path := os.path.join(dir_path, subtitle.file_name)):
            return DownloadResult("already exists", file_path)
        if self._ignore.is_matching(file_path):
            return DownloadResult("explicitly ignored", file_path)
        try:
            r = await client.get(subtitle.url)
        except Exception as e:
            raise DownloadError(subtitle.url) from e
        if r.status_code != httpx.codes.OK:
            return DownloadResult("download failed", file_path)
        with open(file_path, "wb") as f:
            f.write(r.content)
        return DownloadResult("saved", file_path)

    async def download_subs(self, client: httpx.AsyncClient, to_download: Collection[AnimeSubtitleUrl]) -> None:
        for fut in asyncio.as_completed([self.download_sub(client, subtitle) for subtitle in to_download]):
            try:
                print(await fut)
            except DownloadError as e:
                print(f"got {e.errname} while trying to download {e.url}")

    async def sync_all(self) -> None:
        async with httpx.AsyncClient(
            proxies=self._config.proxy,
            headers=self._config.headers,
            timeout=self._config.timeout,
        ) as client:
            state = FetchState.new(self._config.download_root)
            while state.has_unvisited():
                task: FetchResult = await find_subs_all(client, state.to_visit)
                print(f"visited {len(state.to_visit)} pages, found {len(task.to_download)} files.")
                await self.download_subs(client, task.to_download)
                state.balance(task)

        with open(os.path.join(self._config.destination, UPDATED_FILENAME), "w") as of:
            of.write(datetime.utcnow().strftime("%c"))
