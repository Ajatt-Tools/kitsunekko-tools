# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import datetime
import pathlib
import typing

from kitsunekko_tools.api_access.root_directory import format_api_time, parse_api_time
from kitsunekko_tools.common import SKIP_FILES, KitsuError, KitsuException, max_datetime
from kitsunekko_tools.config import Config, KitsuConfig
from kitsunekko_tools.consts import IGNORE_FILENAME
from kitsunekko_tools.filesystem import (
    get_tsv_reader,
    get_tsv_writer,
    iter_subtitle_directories,
    iter_subtitle_files,
)


@dataclasses.dataclass(frozen=True)
class IgnoreListException(KitsuException):
    what: str


def get_ignore_file_path_on_disk(parent_dir: pathlib.Path) -> pathlib.Path:
    """
    Return path to .kitsuignore in this directory.
    """
    return parent_dir.joinpath(IGNORE_FILENAME)


class IgnoreFileEntryDict(typing.TypedDict):
    name: str
    last_modified: str
    st_size: str


@dataclasses.dataclass(frozen=True)
class IgnoreFileEntry:
    name: str
    last_modified: datetime.datetime
    st_size: int

    def to_tsv_row(self) -> IgnoreFileEntryDict:
        as_dict = dataclasses.asdict(self)
        as_dict["last_modified"] = format_api_time(self.last_modified)
        return as_dict


@dataclasses.dataclass(frozen=True)
class FileMetaData(IgnoreFileEntry):
    path: pathlib.Path


def get_modification_time(file_path: pathlib.Path) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(file_path.stat().st_mtime, tz=datetime.UTC)


def pattern_sort_key(pattern: IgnoreFileEntry) -> tuple[str, datetime.datetime, int]:
    return pattern.name, pattern.last_modified, pattern.st_size


class IgnoreTSVForDir:
    """
    Holds a list of files that should not be downloaded even if they're not present in expected locations.
    """

    _ignore_filepath: pathlib.Path
    _patterns: dict[str, IgnoreFileEntry]
    _needs_flush: bool = False

    def __init__(self, ignore_filepath: pathlib.Path) -> None:
        self._ignore_filepath = ignore_filepath
        self._patterns = {}
        self._read_ignore_file()
        self._needs_flush = False

    def _read_ignore_file(self) -> None:
        try:
            with open(self._ignore_filepath, encoding="utf-8", newline="") as f:
                row: IgnoreFileEntryDict
                for row in get_tsv_reader(f):
                    self.add_entry(
                        IgnoreFileEntry(
                            name=row["name"],
                            last_modified=parse_api_time(row["last_modified"]),
                            st_size=int(row["st_size"]),
                        )
                    )
        except FileNotFoundError:
            pass

    @property
    def ignore_filepath(self) -> pathlib.Path:
        """
        Return path to ignore file.
        """
        return self._ignore_filepath

    def file_info(self, file_path: pathlib.Path) -> FileMetaData:
        return FileMetaData(
            **dataclasses.asdict(self._patterns[file_path.name]),
            path=file_path.resolve(),
        )

    def last_modified(self, file_path: pathlib.Path) -> datetime.datetime:
        return self.file_info(file_path).last_modified

    def is_matching(self, file_path: pathlib.Path) -> bool:
        return file_path.name in self._patterns

    def patterns(self) -> typing.Iterable[IgnoreFileEntry]:
        """
        Return all known ignore patterns.
        """
        return self._patterns.values()

    def add_entry(self, file: IgnoreFileEntry) -> None:
        """
        Add a new ignore pattern to the list.
        """
        if not file.name:
            raise IgnoreListException("empty pattern")
        try:
            file = dataclasses.replace(
                file,
                last_modified=max_datetime(file.last_modified, self._patterns[file.name].last_modified),
            )
        except KeyError:
            pass
        self._patterns[file.name] = file
        self._needs_flush = True

    def add_file(self, file_path: pathlib.Path) -> None:
        """
        Add file to the list, as name.
        """
        if not file_path.is_file():
            raise IgnoreListException(f"not a file: {file_path}")
        return self.add_entry(
            IgnoreFileEntry(
                name=file_path.name,
                last_modified=get_modification_time(file_path),
                st_size=file_path.stat().st_size,
            )
        )

    def commit(self) -> None:
        """
        Save ignore file to disk.
        """
        if not self._patterns:
            print(f"empty ignore list: {self._ignore_filepath}")
            return
        if not self._needs_flush:
            return
        with open(self._ignore_filepath, "w", encoding="utf-8") as of:
            writer = get_tsv_writer(of, fieldnames=tuple(IgnoreFileEntry.__annotations__))
            writer.writeheader()
            writer.writerows(entry.to_tsv_row() for entry in sorted(self.patterns(), key=pattern_sort_key))
        print(f"written: {self._ignore_filepath}")


def find_entry_dir(cfg: KitsuConfig, path_to_file: pathlib.Path) -> pathlib.Path:
    for parent_dir in path_to_file.parents:
        if parent_dir.parent in cfg.all_destinations():
            return parent_dir
    raise KitsuError(f"couldn't find location for the {IGNORE_FILENAME} file.")


def add_file_to_ignore_list(cfg: KitsuConfig, path_to_file: pathlib.Path) -> None:
    parent_dir = find_entry_dir(cfg, path_to_file)
    ignore_list = IgnoreTSVForDir(ignore_filepath=get_ignore_file_path_on_disk(parent_dir))
    ignore_list.add_file(path_to_file)
    ignore_list.commit()


def add_all_files_to_ignore_list(cfg: KitsuConfig) -> None:
    cfg.raise_for_destination()
    for directory in iter_subtitle_directories(cfg):
        ignore_list = IgnoreTSVForDir(get_ignore_file_path_on_disk(directory))
        for file in iter_subtitle_files(directory):
            if not ignore_list.is_matching(file):
                # Only add missing files.
                ignore_list.add_file(file)
        ignore_list.commit()
