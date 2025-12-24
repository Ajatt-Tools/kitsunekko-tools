# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import dataclasses
import re

from kitsunekko_tools.consts import IGNORE_FILENAME, INFO_FILENAME, TRASH_DIR_NAME


class KitsuException(Exception, abc.ABC):
    @property
    @abc.abstractmethod
    def what(self) -> str:
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True)
class KitsuError(KitsuException):
    what: str


SKIP_FILES = (IGNORE_FILENAME, INFO_FILENAME, TRASH_DIR_NAME)
RE_FILENAME_PROHIBITED = re.compile(r"[ _\\\n\t\r#{}<>^*/:\"`?'|]+", flags=re.MULTILINE | re.IGNORECASE)
RE_MULTI_SPACE = re.compile(r" {2,}", flags=re.MULTILINE | re.IGNORECASE)
WINDOWS_SUBSTITUTE_CHARS = {
    "??": "2",
    "||": "2",
    "'": "’",
    "\\": "⧵",
    "/": "∕",
    ":": ".",
    "?": "？",
    "|": "⏐",
}
assert all(k != v for k, v in WINDOWS_SUBSTITUTE_CHARS.items())


def fs_name_strip(name: str) -> str:
    for from_, to in WINDOWS_SUBSTITUTE_CHARS.items():
        name = name.replace(from_, to)
    name = re.sub(RE_FILENAME_PROHIBITED, " ", name)
    name = re.sub(RE_MULTI_SPACE, " ", name)
    # Note: Windows-like OSes don't allow dots at the end.
    return name.strip().rstrip(".")
