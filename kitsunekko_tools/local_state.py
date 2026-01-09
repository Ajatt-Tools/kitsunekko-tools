# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import json
import pathlib
import typing

from kitsunekko_tools.api_access.root_directory import (
    ApiDirectoryEntry,
    get_meta_file_path_on_disk,
    parse_api_time,
)
from kitsunekko_tools.entry import DirectoryMetaProtocol, EntryType


@dataclasses.dataclass(frozen=True)
class KitsuDirectoryMeta(ApiDirectoryEntry):
    dir_path: pathlib.Path = pathlib.Path()

    @classmethod
    def from_local_file(cls, f: typing.TextIO, dir_path: pathlib.Path) -> typing.Self:
        return cls(**cls._load_json(f), dir_path=dir_path)

    @staticmethod
    def _load_json(f: typing.TextIO) -> dict:
        data = json.load(f)
        data["last_modified"] = parse_api_time(data["last_modified"])
        data["entry_type"] = EntryType[data["entry_type"]]
        return data

    def write_self_to_file(self) -> None:
        with open(get_meta_file_path_on_disk(self.dir_path), "w", encoding="utf-8") as of:
            self.write_to_file(of)


def read_directory_meta(directory: pathlib.Path) -> KitsuDirectoryMeta:
    with open(get_meta_file_path_on_disk(directory), encoding="utf-8") as f:
        return KitsuDirectoryMeta.from_local_file(f, dir_path=directory)
