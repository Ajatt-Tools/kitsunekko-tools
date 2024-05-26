# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

from kitsunekko_tools.common import fs_name_strip
from kitsunekko_tools.config import KitsuConfig


def move_files(old_dir: pathlib.Path, new_dir: pathlib.Path) -> None:
    for entry in old_dir.iterdir():
        new_path = new_dir / entry.relative_to(old_dir)
        if new_path.exists():
            raise RuntimeError(f"already exists: {new_path}")
        entry.rename(new_path)


def sanitize_directories(config: KitsuConfig) -> None:
    for directory in config.destination.iterdir():
        sanitized_name = fs_name_strip(directory.name)
        if sanitized_name == directory.name:
            continue
        new_dir = directory.parent / sanitized_name
        if new_dir.exists():
            move_files(directory, new_dir)
            directory.rmdir()
        else:
            directory.rename(new_dir)
