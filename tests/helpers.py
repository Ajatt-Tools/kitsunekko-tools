# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import pathlib

from kitsunekko_tools.api_access.root_directory import KitsunekkoId, parse_api_time
from kitsunekko_tools.entry import EntryType
from kitsunekko_tools.ignore import FileMetaData, IgnoreFileEntry
from kitsunekko_tools.local_state import KitsuDirectoryMeta
from kitsunekko_tools.scrapper.types import NoMetaDirectoryEntry
from kitsunekko_tools.website.website import LocalDirectoryEntry


def year(year_: int) -> datetime.datetime:
    """Create a UTC datetime for January 1st of the given year."""
    return datetime.datetime(year=year_, month=1, day=1, tzinfo=datetime.UTC)


def mk_kitsu_meta(*, name: str, year_: int = 2024) -> KitsuDirectoryMeta:
    """Create a KitsuDirectoryMeta for testing."""
    return KitsuDirectoryMeta(
        entry_id=KitsunekkoId(1),
        name=name,
        entry_type=EntryType.anime_tv,
        last_modified=year(year_),
        dir_path=pathlib.Path(f"/tmp/{name}"),
    )


def mk_no_meta(*, name: str, year_: int = 2024) -> NoMetaDirectoryEntry:
    """Create a NoMetaDirectoryEntry for testing."""
    return NoMetaDirectoryEntry(
        dir_path=pathlib.Path(f"/tmp/{name}"),
        name=name,
        last_modified=year(year_),
    )
