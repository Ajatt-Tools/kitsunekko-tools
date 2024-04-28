# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import fnmatch
import pathlib
import typing

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import KitsuConfig, get_config
from kitsunekko_tools.consts import *


@dataclasses.dataclass
class IgnoreListException(KitsuException):
    what: str


class IgnoreList:
    _config: KitsuConfig
    _ignore_filepath: pathlib.Path
    _patterns: dict[str, None]
    _is_dirty: bool

    def __init__(self, config: KitsuConfig | None = None):
        self._config = config or get_config().data
        self._ignore_filepath = pathlib.Path(self._config.destination) / IGNORE_FILENAME
        self._patterns = {}
        self._is_dirty = False
        self._config.raise_for_destination()
        try:
            with open(self._ignore_filepath, encoding="utf8") as f:
                self._patterns.update(dict.fromkeys(filter(bool, map(str.strip, f.read().splitlines()))))
        except FileNotFoundError:
            pass

    @property
    def ignore_filepath(self) -> pathlib.Path:
        return self._ignore_filepath

    def _pattern_from_path(self, file_path: pathlib.Path) -> str:
        return str(file_path.relative_to(self._config.destination))

    def is_matching(self, file_path: pathlib.Path) -> bool:
        path_dest_stripped = self._pattern_from_path(file_path)
        if path_dest_stripped in self._patterns:
            # try without wildcards first.
            return True
        return any(fnmatch.fnmatch(path_dest_stripped, pattern) for pattern in self._patterns)

    def patterns(self) -> typing.Iterable[str]:
        """
        Return all known ignore patterns.
        """
        return self._patterns.keys()

    def add(self, pattern: str):
        """
        Add a new ignore pattern to the list.
        """
        self._patterns[pattern] = None
        self._is_dirty = True

    def add_file(self, file_path: pathlib.Path) -> None:
        """
        Add file to the list, as relative path.
        """
        return self.add(self._pattern_from_path(file_path))

    def path(self) -> pathlib.Path:
        """
        Return path to ignore file.
        """
        return self._ignore_filepath

    def commit(self) -> None:
        """
        Save ignore file to disk.
        """
        if not self._is_dirty:
            return
        self._ignore_filepath.write_text("\n".join(self._patterns))
