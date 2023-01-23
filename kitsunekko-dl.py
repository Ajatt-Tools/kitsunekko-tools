#!/usr/bin/python3
import asyncio
import dataclasses
import json
import os.path
import re
from datetime import datetime
from types import SimpleNamespace
from typing import NewType, Collection
from urllib.parse import unquote

import httpx

PROG = 'kitsunekko-tools'
SETTINGS = 'settings.json'
DOMAIN = "https://kitsunekko.net"
REPO = os.path.abspath(os.path.dirname(__file__))


def get_xdg_config_dir() -> str:
    return os.environ.get('XDG_CONFIG_HOME', os.path.join(os.environ['HOME'], '.config'))


def config_locations():
    return (
        os.path.join(get_xdg_config_dir(), PROG, SETTINGS),
        os.path.join('/etc/', PROG, SETTINGS),
        os.path.join(REPO, SETTINGS),
    )


def read_config():
    for config_file_path in config_locations():
        if os.path.isfile(config_file_path):
            print(f"Reading config file: {config_file_path}")
            with open(config_file_path, encoding='utf8') as f:
                return SimpleNamespace(**json.load(f))
    raise RuntimeError("Couldn't find config file.")


config = read_config()


def file_exists(file_path: str) -> bool:
    return (
            os.path.isfile(file_path)
            and os.stat(file_path).st_size > 0
    )


@dataclasses.dataclass(frozen=True)
class AnimeSubtitleUrl:
    url: str
    title: str


@dataclasses.dataclass(frozen=True)
class FetchResult:
    to_visit: set[str]
    to_download: set[AnimeSubtitleUrl]

    @classmethod
    def new(cls):
        return cls(to_visit=set(), to_download=set())

    def update(self, other: 'FetchResult'):
        self.to_visit.update(other.to_visit)
        self.to_download.update(other.to_download)


DownloadResult = NewType('DownloadResult', str)


@dataclasses.dataclass(frozen=True)
class FetchState:
    to_visit: set[str]
    visited: set[str]

    @classmethod
    def new(cls, download_root: str):
        return cls(to_visit={download_root, }, visited=set())

    def balance(self, prev_result: FetchResult):
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


async def download_sub(client: httpx.AsyncClient, subtitle: AnimeSubtitleUrl) -> DownloadResult:
    if not os.path.isdir(dir_path := os.path.join(config.destination, subtitle.title)):
        os.mkdir(dir_path)
    if file_exists(file_path := os.path.join(dir_path, os.path.basename(unquote(subtitle.url)))):
        return DownloadResult(f"already exists: {file_path}")
    try:
        r = await client.get(subtitle.url)
    except Exception as e:
        raise DownloadError(subtitle.url) from e
    with open(file_path, 'wb') as f:
        f.write(r.content)
    return DownloadResult(f"saved: {file_path}")


async def download_subs(client: httpx.AsyncClient, to_download: Collection[AnimeSubtitleUrl]):
    for fut in asyncio.as_completed([download_sub(client, subtitle) for subtitle in to_download]):
        try:
            print(await fut)
        except DownloadError as e:
            print(f"got {e.errname} while trying to download {e.url}")


def get_anime_title(page_text: str):
    title = re.search(r'<title>([^<>]+)</title>', page_text, flags=re.IGNORECASE | re.MULTILINE).group(1)
    title = (
        title
        .replace(' - Japanese subtitles - kitsunekko.net', '')
        .replace('/', ' ')
        .replace('\\', ' ')
    )
    return title.strip()


async def crawl_page(client: httpx.AsyncClient, url: str) -> FetchResult:
    try:
        r = await client.get(url)
    except Exception as e:
        raise DownloadError(url) from e

    return FetchResult(
        to_visit={
            f'{DOMAIN}/{anime_dir}'
            for anime_dir in re.findall(r'(?<="/)dirlist.php\?[^"\']+(?=")', r.text)
        },
        to_download={
            AnimeSubtitleUrl(f'{DOMAIN}/{subtitle}', get_anime_title(r.text))
            for subtitle in re.findall(r'(?<=href=")subtitles/[^"\']+\.(?:zip|rar|ass|srt)(?=")', r.text)
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


async def main():
    async with httpx.AsyncClient(proxies=config.proxy, headers=config.headers, timeout=config.timeout) as client:
        state = FetchState.new(config.download_root)
        while state.has_unvisited():
            task: FetchResult = await find_subs_all(client, state.to_visit)
            print(f"visited {len(state.to_visit)} pages, found {len(task.to_download)} subtitles.")
            await download_subs(client, task.to_download)
            state.balance(task)

    with open(os.path.join(config.destination, '.updated'), 'w') as of:
        of.write(datetime.utcnow().strftime('%c'))


if __name__ == '__main__':
    asyncio.run(main())
