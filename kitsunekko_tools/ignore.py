# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import pathlib
import typing

from kitsunekko_tools.common import KitsuError, KitsuException
from kitsunekko_tools.config import Config, KitsuConfig
from kitsunekko_tools.consts import IGNORE_FILENAME


@dataclasses.dataclass(frozen=True)
class IgnoreListException(KitsuException):
    what: str


def get_ignore_file_path_on_disk(parent_dir: pathlib.Path) -> pathlib.Path:
    """
    Return path to .kitsuignore in this directory.
    """
    return parent_dir.joinpath(IGNORE_FILENAME)


class IgnoreListForDir:
    """
    Holds a list of files that should not be downloaded even if they're not present in expected locations.
    """

    _ignore_filepath: pathlib.Path
    _patterns: dict[str, None]

    def __init__(self, ignore_filepath: pathlib.Path) -> None:
        self._ignore_filepath = ignore_filepath
        self._patterns = {}
        self._read_ignore_file()

    def _read_ignore_file(self) -> None:
        try:
            for pattern in self._ignore_filepath.read_text(encoding="utf8").splitlines():
                if pattern := pattern.strip():
                    self.add_pattern(pattern)
        except FileNotFoundError:
            pass

    @property
    def ignore_filepath(self) -> pathlib.Path:
        """
        Return path to ignore file.
        """
        return self._ignore_filepath

    def is_matching(self, file_path: pathlib.Path) -> bool:
        return file_path.name in self._patterns

    def patterns(self) -> typing.Iterable[str]:
        """
        Return all known ignore patterns.
        """
        return self._patterns.keys()

    def add_pattern(self, pattern: str) -> None:
        """
        Add a new ignore pattern to the list.
        """
        if not pattern:
            raise IgnoreListException("empty pattern")
        self._patterns[pattern] = None

    def add_file(self, file_path: pathlib.Path) -> None:
        """
        Add file to the list, as name.
        """
        if not file_path.is_file():
            raise IgnoreListException(f"not a file: {file_path}")
        return self.add_pattern(file_path.name)

    def commit(self) -> None:
        """
        Save ignore file to disk.
        """
        if not self._patterns:
            print(f"empty ignore list: {self._ignore_filepath}")
            return
        data = "\n".join(self._patterns) + "\n"
        self._ignore_filepath.write_text(data, encoding="utf-8")  # newline at the end of file
        print(f"written: {self._ignore_filepath}")


def find_entry_dir(cfg: KitsuConfig, path_to_file: pathlib.Path) -> pathlib.Path:
    for parent_dir in path_to_file.parents:
        if parent_dir.parent == cfg.destination:
            return parent_dir
    raise KitsuError(f"couldn't find location for the {IGNORE_FILENAME} file.")


def add_file_to_ignore_list(cfg: KitsuConfig, path_to_file: pathlib.Path) -> None:
    parent_dir = find_entry_dir(cfg, path_to_file)
    ignore_list = IgnoreListForDir(ignore_filepath=get_ignore_file_path_on_disk(parent_dir))
    ignore_list.add_file(path_to_file)
    ignore_list.commit()
