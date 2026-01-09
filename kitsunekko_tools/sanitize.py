# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import collections
import datetime
import pathlib
import shutil
import string
import typing

from kitsunekko_tools.api_access.directory_entry import (
    keep_removed_values,
)
from kitsunekko_tools.api_access.root_directory import (
    ApiDirectoryEntry,
    KitsunekkoId,
    get_meta_file_path,
    get_meta_file_path_on_disk,
)
from kitsunekko_tools.common import SKIP_FILES, KitsuError, fs_name_strip
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import TRASH_DIR_NAME
from kitsunekko_tools.filesystem import iter_subtitle_directories, iter_subtitle_files
from kitsunekko_tools.ignore import IgnoreTSVForDir, get_ignore_file_path_on_disk
from kitsunekko_tools.local_state import KitsuDirectoryMeta, read_directory_meta
from kitsunekko_tools.scrapper.dir_path_matcher import (
    DirPathMatcher,
    MatcherKeyError,
)
from kitsunekko_tools.scrapper.download import unsorted_destination
from kitsunekko_tools.website.website import collect_files


def move_files(old_dir: pathlib.Path, *, new_dir: pathlib.Path) -> None:
    for entry in old_dir.iterdir():
        if entry.is_dir():
            move_files(entry, new_dir=new_dir / entry.name)
            continue
        if entry.name in SKIP_FILES:
            continue
        if not entry.is_file():
            raise KitsuError("entry must be a file.")
        new_path = new_dir / entry.relative_to(old_dir)
        new_path.parent.mkdir(exist_ok=True)
        if new_path.exists():
            entry.unlink()
        else:
            entry.rename(new_path)
    nuke_dir(old_dir)


def nuke_dir(directory: pathlib.Path) -> None:
    get_meta_file_path_on_disk(directory).unlink(missing_ok=True)
    get_ignore_file_path_on_disk(directory).unlink(missing_ok=True)
    directory.rmdir()


def merge_ignore_lists(old_dir: pathlib.Path, *, new_dir: pathlib.Path) -> None:
    old = IgnoreTSVForDir(get_ignore_file_path_on_disk(old_dir))
    new = IgnoreTSVForDir(get_ignore_file_path_on_disk(new_dir))
    for pattern in old.patterns():
        new.add_entry(pattern)
    new.commit()


def rename_badly_named_directories(config: KitsuConfig) -> None:
    print("Renaming badly named directories...")
    for directory in iter_subtitle_directories(config):
        sanitized_name = fs_name_strip(directory.name)
        if sanitized_name == directory.name:
            continue
        new_dir = directory.parent / sanitized_name
        move_directory(directory, new_dir=new_dir)


def merge_metadata(old_dir: pathlib.Path, *, new_dir: pathlib.Path) -> None:
    try:
        old_meta: KitsuDirectoryMeta = read_directory_meta(old_dir)
        new_meta: KitsuDirectoryMeta = read_directory_meta(new_dir)
    except FileNotFoundError:
        return
    with open(get_meta_file_path_on_disk(new_meta.dir_path), "w", encoding="utf-8") as of:
        keep_removed_values(new_meta, old_meta).write_to_file(of)


def move_directory(old_dir: pathlib.Path, *, new_dir: pathlib.Path) -> None:
    """
    Merge two directories. Move all files from directory to the main entry's directory.
    """
    if new_dir == old_dir or not old_dir.is_dir():
        return
    if new_dir.exists():
        print(f"moving '{old_dir}' to '{new_dir}'")
        merge_ignore_lists(old_dir, new_dir=new_dir)
        merge_metadata(old_dir, new_dir=new_dir)
        move_files(old_dir, new_dir=new_dir)
    else:
        print(f"rename '{old_dir}' to '{new_dir}'")
        old_dir.rename(new_dir)


class FixOrphans:
    """
    Try to find metadata for directories without .kitsuinfo.json files.
    """

    _config: KitsuConfig
    _matcher: DirPathMatcher

    def __init__(self, config: KitsuConfig) -> None:
        self._config = config
        self._matcher = DirPathMatcher(self._config)

    def _try_match_by_directory_name(self, dir_path: pathlib.Path) -> None:
        """
        Try to find the main entry by directory name.
        """
        try:
            main_entry = self._matcher.find_best_matching_entry(dir_path.name)
        except MatcherKeyError:
            return
        move_directory(dir_path, new_dir=main_entry.dir_path)

    def merge_directories(self) -> None:
        print("matching orphans...")
        for directory in iter_subtitle_directories(self._config):
            if get_meta_file_path_on_disk(directory).is_file():
                # already has metadata
                continue
            self._try_match_by_directory_name(directory)


def delete_empty_directories(config: KitsuConfig) -> None:
    for directory in iter_subtitle_directories(config):
        files = [*iter_subtitle_files(directory)]
        if not files:
            print(f"deleting empty dir: {directory}")
            nuke_dir(directory)


ASCII_LETTERS = frozenset(string.ascii_letters)


def count_ascii_letters(s: str) -> int:
    """
    Return the number of Latin letters (A-Z, a-z) in s.
    """
    return sum(1 for ch in s if ch in ASCII_LETTERS)


def dir_meta_sort_key(dir_meta: ApiDirectoryEntry) -> tuple[datetime.datetime, int, str]:
    return dir_meta.last_modified, count_ascii_letters(dir_meta.name), dir_meta.name


class DuplicatesGroup(typing.NamedTuple):
    original: KitsuDirectoryMeta
    copies: list[KitsuDirectoryMeta]

    @classmethod
    def from_list(cls, entries: list[KitsuDirectoryMeta]) -> typing.Self:
        if len(entries) < 2:
            raise KitsuError("a group of duplicates should contain at least two files")
        entries = sorted(entries, key=dir_meta_sort_key, reverse=True)
        # Assign the most recently modified entry as the original.
        assert entries[0].last_modified >= entries[1].last_modified
        return cls(original=entries[0], copies=entries[1:])


class MergeSameId:
    def __init__(self, config: KitsuConfig) -> None:
        self._cfg = config

    def _collect_directories_with_same_id(self) -> typing.Sequence[DuplicatesGroup]:
        """
        Find directories that have a .kitsuinfo.json file and matching entry_id.
        Returns a list of groups.
        """
        id_to_entries: dict[KitsunekkoId, list[KitsuDirectoryMeta]] = collections.defaultdict(list)
        print("searching directories with matching entry_id...")
        for directory in iter_subtitle_directories(self._cfg):
            try:
                meta = read_directory_meta(directory)
            except FileNotFoundError:
                continue
            id_to_entries[meta.entry_id].append(meta)
        return [DuplicatesGroup.from_list(entries) for entries in id_to_entries.values() if len(entries) > 1]

    def merge_directories_with_same_id(self) -> None:
        print("Merging directories with matching entry_id...")
        groups = self._collect_directories_with_same_id()
        print(f"found {len(groups)} directories with matching entry_id.")
        for group in groups:
            for copy in group.copies:
                move_directory(copy.dir_path, new_dir=group.original.dir_path)


def organize_by_entry_type(config: KitsuConfig) -> None:
    print("Organizing directories by entry types...")
    for directory in iter_subtitle_directories(config):
        try:
            meta: KitsuDirectoryMeta = read_directory_meta(directory)
        except FileNotFoundError:
            new_dir_path = unsorted_destination(config) / fs_name_strip(directory.name)
        else:
            new_dir_path = get_meta_file_path(meta, config).parent
        if new_dir_path == directory:
            continue
        move_directory(directory, new_dir=new_dir_path)


def make_destination_dirs(config):
    print("Making directories...")
    for directory in config.all_destinations():
        directory.mkdir(exist_ok=True)


def delete_trash_dirs(config: KitsuConfig) -> None:
    for dir_path in iter_subtitle_directories(config):
        trashed_files = []
        other_files = []
        trash_dir = dir_path.joinpath(TRASH_DIR_NAME)
        for file in collect_files(dir_path):
            if file.path.parent == trash_dir:
                trashed_files.append(file)
            else:
                other_files.append(file)
        if other_files and trashed_files:
            print(f"delete dir: {trash_dir}")
            shutil.rmtree(trash_dir)


def sanitize_directories(config: KitsuConfig) -> None:
    make_destination_dirs(config)
    organize_by_entry_type(config)
    rename_badly_named_directories(config)
    MergeSameId(config).merge_directories_with_same_id()
    FixOrphans(config).merge_directories()
