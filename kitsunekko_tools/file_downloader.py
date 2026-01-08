# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import asyncio
import collections
import dataclasses
import datetime
import enum
import pathlib
import typing

import httpx

from kitsunekko_tools.api_access.directory_entry import KitsuDirectoryEntry
from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.ignore import IgnoreFileEntry, IgnoreTSVForDir

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


@dataclasses.dataclass(frozen=True)
class KitsuSubtitleDownload:
    url: SubtitleFileUrl
    file_path: pathlib.Path
    last_modified_on_remote: datetime.datetime
    entry: KitsuDirectoryEntry | None = None

    def ensure_subtitle_dir(self) -> None:
        """
        Create directory to store the subtitle files.
        """
        return self.file_path.parent.mkdir(exist_ok=True)

    def is_already_downloaded(self) -> bool:
        return is_file_non_empty(self.file_path)


@dataclasses.dataclass(frozen=True)
class DownloadSubtitlesList:
    to_download: list[KitsuSubtitleDownload]
    ignore_list: IgnoreTSVForDir


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


def get_ignore_entry_from_download(subtitle: KitsuSubtitleDownload) -> IgnoreFileEntry:
    return IgnoreFileEntry(
        name=subtitle.file_path.name,
        last_modified=subtitle.last_modified_on_remote,
        st_size=subtitle.file_path.stat().st_size,
    )


def should_add_to_ignore_list(ignore_list: IgnoreTSVForDir, result: DownloadResult) -> bool:
    match result.reason:
        case DownloadStatus.saved:
            return True
        case DownloadStatus.already_exists if not ignore_list.is_matching(result.subtitle.file_path):
            return True
        case _:
            return False
    raise RuntimeError("unreachable")


class KitsuSubtitleDownloader:
    def __init__(self, config: KitsuConfig):
        self._config = config

    async def download_subs(
        self,
        client: httpx.AsyncClient,
        entry: DownloadSubtitlesList,
    ) -> KitsuDownloadResults:
        tasks = tuple(self.download_sub(client, sub, entry.ignore_list) for sub in entry.to_download)
        results = KitsuDownloadResults()
        for fut in asyncio.as_completed(tasks):
            try:
                result: DownloadResult = await fut
            except KitsuConnectionError as ex:
                print(ex)
            else:
                print(result)
                results.add_result(result)
                if should_add_to_ignore_list(entry.ignore_list, result):
                    # this file will not be downloaded again even if it is moved(renamed) later.
                    entry.ignore_list.add_entry(get_ignore_entry_from_download(result.subtitle))
        entry.ignore_list.commit()
        return results

    def _should_skip_download(
        self, subtitle: KitsuSubtitleDownload, ignore_list: IgnoreTSVForDir
    ) -> DownloadStatus | None:
        if not self._config.is_allowed_file_type(subtitle.file_path):
            return DownloadStatus.blocked_file_type

        try:
            if ignore_list.last_modified(subtitle.file_path) < subtitle.last_modified_on_remote:
                # Our file is older than theirs
                print(f"remote is newer: {subtitle.file_path}")
                return None
        except KeyError:
            pass

        if subtitle.is_already_downloaded():
            return DownloadStatus.already_exists

        if ignore_list.is_matching(subtitle.file_path):
            return DownloadStatus.explicitly_ignored

        return None

    async def download_sub(
        self, client: httpx.AsyncClient, subtitle: KitsuSubtitleDownload, ignore_list: IgnoreTSVForDir
    ) -> DownloadResult:
        if skip_reason := self._should_skip_download(subtitle, ignore_list):
            return DownloadResult(reason=skip_reason, subtitle=subtitle)

        print(f"downloading file: {subtitle.url}")

        try:
            r = await client.get(subtitle.url)
        except Exception as e:
            raise KitsuConnectionError(subtitle.url) from e

        if r.status_code != httpx.codes.OK:
            return DownloadResult(reason=DownloadStatus.download_failed, subtitle=subtitle, status_code=r.status_code)

        subtitle.ensure_subtitle_dir()
        subtitle.file_path.write_bytes(r.content)
        return DownloadResult(reason=DownloadStatus.saved, subtitle=subtitle, status_code=r.status_code)
