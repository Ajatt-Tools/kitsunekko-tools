# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

from kitsunekko_tools.api_access.root_directory import KitsuDirectoryMeta, EntryId
from kitsunekko_tools.common import fs_name_strip
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import INFO_FILENAME, IGNORE_FILENAME

SKIP_FILES = (IGNORE_FILENAME, INFO_FILENAME)


def move_files(old_dir: pathlib.Path, new_dir: pathlib.Path) -> None:
    for entry in old_dir.iterdir():
        if entry.name in SKIP_FILES:
            continue
        new_path = new_dir / entry.relative_to(old_dir)
        if new_path.exists():
            entry.unlink()
        else:
            entry.rename(new_path)


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
            nuke_dir(directory)
        else:
            directory.rename(new_dir)


def merge_directories(config: KitsuConfig) -> None:
    id2master: dict[EntryId, KitsuDirectoryMeta] = {}
    name2id: dict[str, EntryId] = {}

    for directory in config.destination.iterdir():
        if directory.name in SKIP_FILES:
            continue
        try:
            with open(directory / INFO_FILENAME, encoding="utf-8") as f:
                meta = KitsuDirectoryMeta.from_local_file(f, dir_path=directory)
        except FileNotFoundError:
            continue

        if meta.entry_id not in id2master:
            id2master[meta.entry_id] = meta
        else:
            id2master[meta.entry_id] = meta = max(meta, id2master[meta.entry_id], key=lambda d: d.last_modified)

        name2id[directory.name.lower()] = meta.entry_id
        if meta.english_name:
            name2id[meta.english_name.lower()] = meta.entry_id
        if meta.japanese_name:
            name2id[meta.japanese_name.lower()] = meta.entry_id

    for directory in config.destination.iterdir():
        try:
            master_entry = id2master[name2id[directory.name.lower()]]
        except KeyError:
            continue
        if master_entry.dir_path == directory:
            continue
        else:
            print(f"moving '{directory}' to '{master_entry.dir_path}'")
            move_files(directory, master_entry.dir_path)
            nuke_dir(directory)


def sanitize_directories(config: KitsuConfig) -> None:
    rename_badly_named_directories(config)
    merge_directories(config)
