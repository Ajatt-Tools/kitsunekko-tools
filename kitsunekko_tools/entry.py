# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import enum
import typing


class ApiDirectoryFlagsDict(typing.TypedDict):
    adult: bool
    anime: bool
    external: bool
    low_quality: bool
    movie: bool


@enum.unique
class EntryType(enum.Enum):
    anime_tv = "Anime TV"
    anime_movie = "Anime movie"
    drama_tv = "Drama TV"
    drama_movie = "Drama movie"
    unsorted = "Unsorted"


def describe_entry_type(flags: ApiDirectoryFlagsDict) -> EntryType:
    return EntryType[f'{"anime" if flags["anime"] else "drama"}_{"movie" if flags["movie"] else "tv"}']


class DirectoryMetaProtocol(typing.Protocol):
    name: str
    entry_type: EntryType
    english_name: None | str
    japanese_name: None | str
    last_modified: datetime.datetime

    @property
    def fs_name(self) -> str: ...
