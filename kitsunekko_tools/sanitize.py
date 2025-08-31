# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
from typing import Iterable

from kitsunekko_tools.api_access.root_directory import EntryId, KitsuDirectoryMeta
from kitsunekko_tools.common import fs_name_strip
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import IGNORE_FILENAME, INFO_FILENAME, TRASH_DIR_NAME

SKIP_FILES = (IGNORE_FILENAME, INFO_FILENAME, TRASH_DIR_NAME)


def move_files(old_dir: pathlib.Path, new_dir: pathlib.Path) -> None:
    for entry in old_dir.iterdir():
        if entry.is_dir():
            move_files(entry, new_dir / entry.name)
            continue
        if entry.name in SKIP_FILES:
            continue
        assert entry.is_file(), "entry must be a file."
        new_path = new_dir / entry.relative_to(old_dir)
        new_path.parent.mkdir(exist_ok=True)
        if new_path.exists():
            entry.unlink()
        else:
            entry.rename(new_path)
    nuke_dir(old_dir)


def nuke_dir(directory: pathlib.Path) -> None:
    (directory / INFO_FILENAME).unlink(missing_ok=True)
    directory.rmdir()


def rename_badly_named_directories(config: KitsuConfig) -> None:
    for directory in config.destination.iterdir():
        if directory.name in SKIP_FILES:
            continue
        sanitized_name = fs_name_strip(directory.name)
        if sanitized_name == directory.name:
            continue
        new_dir = directory.parent / sanitized_name
        print(f"moving '{directory}' to '{new_dir}'")
        if new_dir.exists():
            move_files(directory, new_dir)
        else:
            directory.rename(new_dir)


def read_directory_meta(directory: pathlib.Path) -> KitsuDirectoryMeta:
    with open(directory / INFO_FILENAME, encoding="utf-8") as f:
        return KitsuDirectoryMeta.from_local_file(f, dir_path=directory)


def move_directory(directory: pathlib.Path, main_entry: KitsuDirectoryMeta) -> None:
    """
    Merge two directories. Move all files from directory to the main entry's directory.
    """
    if main_entry.dir_path != directory:
        print(f"moving '{directory}' to '{main_entry.dir_path}'")
        move_files(directory, main_entry.dir_path)


def iter_lookup_keys(meta: KitsuDirectoryMeta) -> Iterable[str]:
    assert meta.entry_type, "entry type shouldn't be empty."
    assert meta.entry_id >= 0, "entry id shouldn't be empty."
    assert meta.dir_path.is_dir(), "entry directory should exist."
    assert meta.name, "entry name should exist."

    # Using IDs (high priority)
    yield f"kitsunekko_{meta.entry_id}"
    if meta.anilist_id:
        yield f"anilist_{meta.anilist_id}"
    if meta.tmdb_id:
        yield f"tmdb_{meta.tmdb_id}"

    # Using type + name
    yield f"{meta.entry_type}_{meta.name.lower()}"
    if meta.english_name:
        yield f"{meta.entry_type}_{meta.english_name.lower()}"
    if meta.japanese_name:
        yield f"{meta.entry_type}_{meta.japanese_name.lower()}"

    # Using just name
    yield meta.name.lower()
    if meta.english_name:
        yield meta.english_name.lower()
    if meta.japanese_name:
        yield meta.japanese_name.lower()
    yield meta.dir_path.name.lower()


class MergeDirectories:
    _config: KitsuConfig
    _id_to_main_entry: dict[EntryId, KitsuDirectoryMeta]
    _lookup_key_to_id: dict[str, EntryId]

    def __init__(self, config: KitsuConfig) -> None:
        self._config = config
        self._id_to_main_entry = {}
        self._lookup_key_to_id = {}

    def _build_lookup_dicts(self) -> None:
        for directory in self._config.destination.iterdir():
            if directory.name in SKIP_FILES:
                continue
            try:
                meta = read_directory_meta(directory)
            except FileNotFoundError:
                continue

            # Main entry is the most recently modified directory with this ID.
            if meta.entry_id not in self._id_to_main_entry:
                self._id_to_main_entry[meta.entry_id] = meta
            else:
                self._id_to_main_entry[meta.entry_id] = meta = max(
                    meta,
                    self._id_to_main_entry[meta.entry_id],
                    key=lambda d: d.last_modified,
                )
            for lookup_key in iter_lookup_keys(meta):
                self._lookup_key_to_id[lookup_key] = meta.entry_id

    def _find_main_entry(self, meta: KitsuDirectoryMeta) -> KitsuDirectoryMeta:
        # Try to find the main entry by different names and IDs.
        for try_key in iter_lookup_keys(meta):
            try:
                return self._id_to_main_entry[self._lookup_key_to_id[try_key]]
            except KeyError:
                pass
        raise KeyError("Tried all possible lookup keys and found nothing.")

    def _try_match_by_directory_name(self, directory: pathlib.Path) -> None:
        """
        Try to find the main entry by directory name.
        """
        try:
            main_entry = self._id_to_main_entry[self._lookup_key_to_id[directory.name.lower()]]
        except KeyError:
            return
        move_directory(directory, main_entry)

    def _find_matches_and_merge(self) -> None:
        for directory in self._config.destination.iterdir():
            if directory.name in SKIP_FILES:
                continue
            try:
                meta = read_directory_meta(directory)
            except FileNotFoundError:
                self._try_match_by_directory_name(directory)
                continue

            try:
                main_entry = self._find_main_entry(meta)
            except (KeyError, FileNotFoundError):
                self._try_match_by_directory_name(directory)
                continue

            move_directory(directory, main_entry)

    def merge_directories(self) -> None:
        self._build_lookup_dicts()
        self._find_matches_and_merge()


def delete_empty_directories(config: KitsuConfig) -> None:
    for directory in config.destination.iterdir():
        if directory.name in SKIP_FILES:
            continue
        entries = [entry for entry in directory.iterdir() if entry.name not in SKIP_FILES]
        try:
            extra_files = [*directory.joinpath(TRASH_DIR_NAME).iterdir()]
        except FileNotFoundError:
            extra_files = []
        if not entries and not extra_files:
            print(f"deleting empty dir: {directory}")
            nuke_dir(directory)


def sanitize_directories(config: KitsuConfig) -> None:
    rename_badly_named_directories(config)
    MergeDirectories(config).merge_directories()
    delete_empty_directories(config)
