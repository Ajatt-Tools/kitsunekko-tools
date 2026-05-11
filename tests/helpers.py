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


def mk_ignore_entry(*, name: str, st_size: int = 100, year_: int = 2024) -> IgnoreFileEntry:
    """Create an IgnoreFileEntry for testing."""
    return IgnoreFileEntry(name=name, last_modified=year(year_), st_size=st_size)


def mk_real_ignore_entry(*, name: str, st_size: int, last_modified: str) -> IgnoreFileEntry:
    """Create an IgnoreFileEntry from real API data."""
    return IgnoreFileEntry(name=name, last_modified=parse_api_time(last_modified), st_size=st_size)


def mk_entry(*, name: str, year_: int = 0, has_meta: bool = True) -> LocalDirectoryEntry:
    """Create a LocalDirectoryEntry for testing."""
    meta = mk_kitsu_meta(name=name, year_=year_) if has_meta else None
    return LocalDirectoryEntry(
        meta=meta,
        path_to_dir=pathlib.Path(f"/tmp/{name}"),
        files_in_dir=[],
        site_path_to_html_file=pathlib.Path(f"/site/{name}.html"),
        is_drama=False,
    )


