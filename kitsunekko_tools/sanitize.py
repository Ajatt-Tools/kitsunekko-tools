# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import collections
import datetime
import pathlib
import re
import typing
from collections.abc import Iterable

from kitsunekko_tools.api_access.directory_entry import (
    get_meta_file_path_on_disk,
    keep_removed_values,
)
from kitsunekko_tools.api_access.root_directory import KitsuDirectoryMeta, KitsunekkoId
from kitsunekko_tools.common import SKIP_FILES, KitsuError, fs_name_strip
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.filesystem import iter_subtitle_directories, iter_subtitle_files
from kitsunekko_tools.ignore import IgnoreTSVForDir, get_ignore_file_path_on_disk

RE_INSIGNIFICANT_CHARS = re.compile(
    r"[\- ー,.。、！!@#$%^&*()_=+＠＃＄％＾△＆＊（）＋＝「」\s\\\n\t\r\[\]{}<>?/\'\":`|;〄〇〈〉〓〔〕〖〗〘〙〚〛〝〞〟〠〡〢〣〥〦〧〨〭〮〯〫〬〶〷〸〹〺〻〼〾〿？…ヽヾゞ〱〲〳〵〴［］｛｝｟｠゠‥•◦﹅﹆♪♫♬♩ⓍⓁⓎ仝　・※【】〒◎×〃゜『』《》～〜~〽☆∀∕]+",
    flags=re.MULTILINE | re.IGNORECASE,
)


def move_files(old_dir: pathlib.Path, new_dir: pathlib.Path) -> None:
    for entry in old_dir.iterdir():
        if entry.is_dir():
            move_files(entry, new_dir / entry.name)
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


def merge_ignore_lists(old_dir: pathlib.Path, new_dir: pathlib.Path) -> None:
    old = IgnoreTSVForDir(get_ignore_file_path_on_disk(old_dir))
    new = IgnoreTSVForDir(get_ignore_file_path_on_disk(new_dir))
    for pattern in old.patterns():
        new.add_entry(pattern)
    new.commit()


def rename_badly_named_directories(config: KitsuConfig) -> None:
    for directory in iter_subtitle_directories(config):
        sanitized_name = fs_name_strip(directory.name)
        if sanitized_name == directory.name:
            continue
        new_dir = directory.parent / sanitized_name
        print(f"moving '{directory}' to '{new_dir}'")
        if new_dir.exists():
            merge_ignore_lists(directory, new_dir)
            move_files(directory, new_dir)
        else:
            directory.rename(new_dir)


def read_directory_meta(directory: pathlib.Path) -> KitsuDirectoryMeta:
    with open(get_meta_file_path_on_disk(directory), encoding="utf-8") as f:
        return KitsuDirectoryMeta.from_local_file(f, dir_path=directory)


def merge_metadata(old_dir: pathlib.Path, new_dir: pathlib.Path) -> None:
    try:
        old_meta: KitsuDirectoryMeta = read_directory_meta(old_dir)
        new_meta: KitsuDirectoryMeta = read_directory_meta(new_dir)
    except FileNotFoundError:
        return
    with open(get_meta_file_path_on_disk(new_meta.dir_path), "w", encoding="utf-8") as of:
        keep_removed_values(new_meta, old_meta).write_to_file(of)


def move_directory(directory: pathlib.Path, main_entry: KitsuDirectoryMeta) -> None:
    """
    Merge two directories. Move all files from directory to the main entry's directory.
    """
    if main_entry.dir_path != directory:
        print(f"moving '{directory}' to '{main_entry.dir_path}'")
        merge_ignore_lists(directory, new_dir=main_entry.dir_path)
        merge_metadata(directory, new_dir=main_entry.dir_path)
        move_files(directory, new_dir=main_entry.dir_path)


def name_strip_insignificant_chars(name: str) -> str:
    return re.sub(RE_INSIGNIFICANT_CHARS, "", name).lower()


def iter_lookup_keys(meta: KitsuDirectoryMeta) -> Iterable[str]:
    if meta.name:
        yield name_strip_insignificant_chars(meta.name)
    if meta.english_name:
        yield name_strip_insignificant_chars(meta.english_name)
    if meta.japanese_name:
        yield name_strip_insignificant_chars(meta.japanese_name)
    yield meta.dir_path.name.lower()
    yield name_strip_insignificant_chars(meta.dir_path.name)


class FixOrphans:
    """
    Try to find metadata for directories without .kitsuinfo.json files.
    """

    _config: KitsuConfig
    _lookup_key_to_meta: dict[str, KitsuDirectoryMeta]

    def __init__(self, config: KitsuConfig) -> None:
        self._config = config
        self._lookup_key_to_meta = {}

    def _build_lookup_dicts(self) -> None:
        print("building lookup dict to match orphans...")
        for directory in iter_subtitle_directories(self._config):
            try:
                meta = read_directory_meta(directory)
            except FileNotFoundError:
                continue
            if not meta.entry_id:
                continue
            for lookup_key in iter_lookup_keys(meta):
                self._lookup_key_to_meta[lookup_key] = meta

    def _try_match_by_directory_name(self, dir_path: pathlib.Path) -> None:
        """
        Try to find the main entry by directory name.
        """
        for try_key in (dir_path.name.lower(), name_strip_insignificant_chars(dir_path.name)):
            try:
                main_entry = self._lookup_key_to_meta[try_key]
            except KeyError:
                continue
            move_directory(dir_path, main_entry)
            break

    def _find_matches_and_merge(self) -> None:
        print("matching orphans...")
        for directory in iter_subtitle_directories(self._config):
            if get_meta_file_path_on_disk(directory).is_file():
                # already has metadata
                continue
            self._try_match_by_directory_name(directory)

    def merge_directories(self) -> None:
        self._build_lookup_dicts()
        self._find_matches_and_merge()


def delete_empty_directories(config: KitsuConfig) -> None:
    for directory in iter_subtitle_directories(config):
        files = [*iter_subtitle_files(directory)]
        if not files:
            print(f"deleting empty dir: {directory}")
            nuke_dir(directory)


def dir_sort_key_by_last_modified(dir_meta: KitsuDirectoryMeta) -> datetime.datetime:
    return dir_meta.last_modified


class DuplicatesGroup(typing.NamedTuple):
    original: KitsuDirectoryMeta
    copies: list[KitsuDirectoryMeta]

    @classmethod
    def from_list(cls, entries: list[KitsuDirectoryMeta]) -> typing.Self:
        if len(entries) < 2:
            raise KitsuError("a group of duplicates should contain at least two files")
        entries = sorted(entries, key=dir_sort_key_by_last_modified, reverse=True)
        # Assign the most recently modified entry as the original.
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
        groups = self._collect_directories_with_same_id()
        print(f"found {len(groups)} directories with matching entry_id.")
        for group in groups:
            for copy in group.copies:
                move_directory(copy.dir_path, group.original)


def sanitize_directories(config: KitsuConfig) -> None:
    rename_badly_named_directories(config)
    MergeSameId(config).merge_directories_with_same_id()
    FixOrphans(config).merge_directories()
    delete_empty_directories(config)
