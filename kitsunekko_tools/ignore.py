# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import fnmatch
import os.path
import pathlib
import sys
import typing

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import get_config, KitsuConfig
from kitsunekko_tools.consts import *


@dataclasses.dataclass
class IgnoreListException(KitsuException):
    what: str


class IgnoreList:
    _config: KitsuConfig
    _ignore_filepath: pathlib.Path

    def __init__(self, config: KitsuConfig | None = None):
        self._config = config or get_config().data
        self._ignore_filepath = pathlib.Path(self._config.destination) / IGNORE_FILENAME
        self._patterns = set()
        if not self._config.destination.is_dir():
            raise IgnoreListException(f"Destination directory does not exist: {self._config.destination}")
        try:
            with open(self._ignore_filepath, encoding="utf8") as f:
                print(f"Reading ignore file: {self._ignore_filepath}", file=sys.stderr)
                self._patterns.update(filter(bool, map(str.strip, f.read().splitlines())))
        except FileNotFoundError:
            pass

    def is_matching(self, file_path: str) -> bool:
        path_dest_stripped = os.path.relpath(file_path, self._config.destination)
        return any(fnmatch.fnmatch(path_dest_stripped, pattern) for pattern in self._patterns)

    def patterns(self) -> set[str]:
        """
        Return all known ignore patterns.
        """
        return self._patterns

    def add(self, pattern: str):
        """
        Add a new ignore pattern to the list.
        """
        self._patterns.add(pattern)
        self._ignore_filepath.write_text("\n".join(self._patterns))

    def path(self) -> pathlib.Path:
        """
        Return path to ignore file.
        """
        return self._ignore_filepath
