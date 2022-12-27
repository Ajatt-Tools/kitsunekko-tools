#!/usr/bin/python3
import asyncio
import dataclasses
import itertools
import json
import os.path
import re
from types import SimpleNamespace
from urllib.parse import unquote

import httpx

DOMAIN = "https://kitsunekko.net"
DOWNLOAD_ROOT = f"{DOMAIN}/dirlist.php?dir=subtitles/japanese/"
REPO = os.path.abspath(os.path.dirname(__file__))


def read_config():
    with open(os.path.join(REPO, 'settings.json'), encoding='utf8') as f:
        return SimpleNamespace(**json.load(f))


config = read_config()


def file_exists(file_path: str) -> bool:
    return (
            os.path.isfile(file_path)
            and os.stat(file_path).st_size > 0
    )


async def download_sub(client: httpx.AsyncClient, url: str, anime_title: str):
    if not os.path.isdir(dir_path := os.path.join(config.destination, anime_title)):
        os.mkdir(dir_path)
    if not file_exists(file_path := os.path.join(dir_path, os.path.basename(unquote(url)))):
        try:
            r = await client.get(url)
        except (
                asyncio.exceptions.CancelledError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
                httpx.ProxyError,
                httpx.PoolTimeout,
        ):
            return print(f"cancelled: {file_path}")
        with open(file_path, 'wb') as f:
            f.write(r.content)
        return print(f"saved: {file_path}")
    else:
        return print(f"already exists: {file_path}")


def get_anime_title(page_text: str):
    title = re.search(r'<title>([^<>]+)</title>', page_text, flags=re.IGNORECASE | re.MULTILINE).group(1)
    title = (
        title
        .replace(' - Japanese subtitles - kitsunekko.net', '')
        .replace('/', ' ')
        .replace('\\', ' ')
    )
    return title.strip()


@dataclasses.dataclass(frozen=True)
class AnimeSubtitleUrl:
    url: str
    title: str


@dataclasses.dataclass(frozen=True)
class PageFetchResult:
    to_visit: set[str]
    to_download: set[AnimeSubtitleUrl]


async def find_subs(client: httpx.AsyncClient, url: str):
    r = await client.get(url)

    subtitle_urls = set()
    for subtitle in re.findall(r'(?<=href=")subtitles/[^"\']+\.(?:zip|rar|ass|srt)(?=")', r.text):
        subtitle_urls.add(AnimeSubtitleUrl(f'{DOMAIN}/{subtitle}', get_anime_title(r.text)))

    unvisited_pages = set()
    for anime_dir in re.findall(r'(?<="/)dirlist.php\?[^"\']+(?=")', r.text):
        unvisited_pages.add(f'{DOMAIN}/{anime_dir}')

    return PageFetchResult(unvisited_pages, subtitle_urls)


async def main():
    async with httpx.AsyncClient(proxies=config.proxy, headers=config.headers, timeout=config.timeout) as client:
        to_visit: set[str] = {DOWNLOAD_ROOT, }
        visited_pages: set[str] = set()

        while to_visit:
            results = await asyncio.gather(*[find_subs(client, page) for page in to_visit])
            visited_pages.update(to_visit)

            to_download: set[AnimeSubtitleUrl] = set(itertools.chain(*[result.to_download for result in results]))
            to_visit: set[str] = set(itertools.chain(*[result.to_visit for result in results])) - visited_pages

            print(f"visited {len(visited_pages)} pages, found {len(to_download)} subtitles.")

            await asyncio.gather(*[download_sub(client, subtitle.url, subtitle.title) for subtitle in to_download])


if __name__ == '__main__':
    asyncio.run(main())
