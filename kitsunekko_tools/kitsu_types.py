# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import typing


class CompareError(ValueError):
    def __init__(self, obj1, obj2):
        super().__init__(f"Can't compare type {type(obj1).__name__} to type {type(obj2).__name__}")


class AnimeDir(typing.NamedTuple):
    url: str  # full URL to the directory with subtitle files
    show_name: str  # name of the anime
    mod_timestamp: datetime.datetime  # last modified

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AnimeDir):
            raise CompareError(self, other)
        return self.show_name == other.show_name

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.show_name)


class SubtitleFile(typing.NamedTuple):
    url: str  # full URL to the subtitle file
    show_name: str  # anime title
    file_name: str  # name of the subtitle file
    mod_timestamp: datetime.datetime  # last modified

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SubtitleFile):
            raise CompareError(self, other)
        return self.show_name == other.show_name and self.file_name == other.file_name

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(f"{self.show_name}/{self.file_name}")
