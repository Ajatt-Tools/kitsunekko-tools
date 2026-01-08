# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import dataclasses
import datetime
import re

from kitsunekko_tools.consts import IGNORE_FILENAME, INFO_FILENAME, TRASH_DIR_NAME
from kitsunekko_tools.entry import EntryType


class KitsuException(Exception, abc.ABC):
    what: str


@dataclasses.dataclass(frozen=True)
class KitsuError(KitsuException):
    what: str


SKIP_FILES = (IGNORE_FILENAME, INFO_FILENAME, TRASH_DIR_NAME, *(et.name for et in EntryType))
RE_FILENAME_PROHIBITED = re.compile(r"[ _\\\n\t\r#{}<>^*/:\"`?'|]+", flags=re.MULTILINE | re.IGNORECASE)
RE_MULTI_SPACE = re.compile(r"\s{2,}", flags=re.MULTILINE | re.IGNORECASE)
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
    return name.strip().strip(" .")


def datetime_now_utc() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


def max_datetime(t1: datetime.datetime, t2: datetime.datetime) -> datetime.datetime:
    return min(datetime_now_utc(), max(t1, t2))


def epoch_datetime() -> datetime.datetime:
    return datetime.datetime.fromtimestamp(0, tz=datetime.UTC)
