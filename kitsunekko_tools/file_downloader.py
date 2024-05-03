# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import asyncio
import collections
import dataclasses
import enum
import pathlib
import typing

import httpx

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.ignore import IgnoreList

SubtitleFileUrl = typing.NewType("SubtitleFileUrl", str)


@dataclasses.dataclass(frozen=True)
class KitsuConnectionError(KitsuException):
    """
    Failed to connect. Raised from another exception.
    """

    url: str

    @property
    def what(self) -> str:
        return type(self.__cause__).__name__

    def __str__(self) -> str:
        return f"got {self.what} while trying to download {self.url}"


def is_file_non_empty(file_path: pathlib.Path) -> bool:
    """
    Returns True if file exists and is not empty.
    """
    return file_path.is_file() and file_path.stat().st_size > 0


class KitsuSubtitleDownload(typing.NamedTuple):
    url: SubtitleFileUrl
    file_path: pathlib.Path

    def ensure_subtitle_dir(self) -> None:
        """
        Create directory to store the subtitle files.
        """
        return self.file_path.parent.mkdir(exist_ok=True)

    def is_already_downloaded(self) -> bool:
        return is_file_non_empty(self.file_path)


@enum.unique
class DownloadStatus(enum.Enum):
    already_exists = enum.auto()
    explicitly_ignored = enum.auto()
    blocked_file_type = enum.auto()
    download_failed = enum.auto()
    saved = enum.auto()

    def __str__(self) -> str:
        return self.name.replace("_", " ")


class DownloadResult(typing.NamedTuple):
    reason: DownloadStatus
    subtitle: KitsuSubtitleDownload
    status_code: int = 0

    def __repr__(self):
        if self.reason == DownloadStatus.download_failed:
            return f"{self.reason} with status {self.status_code}: {self.subtitle.url}"
        return f"{self.reason}: {self.subtitle.url}"

    def is_successful(self) -> bool:
        return self.reason == DownloadStatus.already_exists or self.reason == DownloadStatus.saved


class KitsuDownloadResults(collections.Counter):
    def add_result(self, result: DownloadResult):
        self[result.reason] += 1

    def num_saved(self) -> int:
        return self[DownloadStatus.saved]

    def num_failed(self) -> int:
        return self[DownloadStatus.download_failed]


class KitsuSubtitleDownloader:
    def __init__(self, config: KitsuConfig, ignore_list: IgnoreList):
        self._config = config
        self._ignore = ignore_list

    async def download_subs(
        self,
        client: httpx.AsyncClient,
        to_download: typing.Sequence[KitsuSubtitleDownload],
    ) -> KitsuDownloadResults:
        tasks = tuple(self.download_sub(client, sub) for sub in to_download)
        results = KitsuDownloadResults()
        for fut in asyncio.as_completed(tasks):
            try:
                result = await fut
            except KitsuConnectionError as ex:
                print(ex)
            else:
                print(result)
                if result.is_successful():
                    # this file will not be downloaded again even if it is moved later.
                    self._ignore.add_file(result.subtitle.file_path)
                self._ignore.maybe_commit_midway()
                results.add_result(result)
        self._ignore.commit()
        return results

    async def download_sub(self, client: httpx.AsyncClient, subtitle: KitsuSubtitleDownload) -> DownloadResult:
        if subtitle.is_already_downloaded():
            return DownloadResult(DownloadStatus.already_exists, subtitle)

        if self._ignore.is_matching(subtitle.file_path):
            return DownloadResult(DownloadStatus.explicitly_ignored, subtitle)

        if not self._config.is_allowed_file_type(subtitle.file_path):
            return DownloadResult(DownloadStatus.blocked_file_type, subtitle)

        print(f"downloading file: {subtitle.url}")

        try:
            r = await client.get(subtitle.url)
        except Exception as e:
            raise KitsuConnectionError(subtitle.url) from e

        if r.status_code != httpx.codes.OK:
            return DownloadResult(DownloadStatus.download_failed, subtitle, r.status_code)

        subtitle.ensure_subtitle_dir()
        subtitle.file_path.write_bytes(r.content)
        return DownloadResult(DownloadStatus.saved, subtitle, r.status_code)
