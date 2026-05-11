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
