# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import pathlib
import typing

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import IGNORE_FILENAME


@dataclasses.dataclass(frozen=True)
class IgnoreListException(KitsuException):
    what: str


class IgnoreList:
    """
    Holds a list of files that should not be downloaded even if they're not present in expected locations.
    """

    _config: KitsuConfig
    _ignore_filepath: pathlib.Path
    _patterns: dict[str, None]
    _dirty_level: int  # counts additions
    _autocommit_threshold: int

    def __init__(self, config: KitsuConfig, autocommit_threshold: int = 20):
        self._config = config
        self._ignore_filepath = pathlib.Path(self._config.destination) / IGNORE_FILENAME
        self._patterns = {}
        self._dirty_level = 0
        self._autocommit_threshold = autocommit_threshold
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
        return self._pattern_from_path(file_path) in self._patterns

    def patterns(self) -> typing.Iterable[str]:
        """
        Return all known ignore patterns.
        """
        return self._patterns.keys()

    def add(self, pattern: str) -> None:
        """
        Add a new ignore pattern to the list.
        """
        self._patterns[pattern] = None
        self._dirty_level += 1

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
        if self._dirty_level == 0:
            return
        data = "\n".join(self._patterns) + "\n"
        self._ignore_filepath.write_text(data, encoding="utf-8")  # newline at the end of file
        self._dirty_level = 0

    def maybe_commit_midway(self) -> None:
        """
        Save file to disk if its dirty level exceeds the set limit.
        """
        if self._dirty_level >= self._autocommit_threshold:
            self.commit()
