# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import datetime
import json
import pathlib
import typing
from collections.abc import Sequence
from pprint import pprint

from kitsunekko_tools.common import fs_name_strip
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import INFO_FILENAME
from kitsunekko_tools.entry import (
    ApiDirectoryFlagsDict,
    DirectoryMetaProtocol,
    EntryType,
    describe_entry_type,
)


class ApiDirectoryDict(typing.TypedDict):
    id: int
    english_name: str
    flags: ApiDirectoryFlagsDict
    japanese_name: str
    last_modified: str
    name: str
    notes: typing.NotRequired[str]
    tmdb_id: typing.NotRequired[str]
    anilist_id: typing.NotRequired[int]
    creator_id: typing.NotRequired[int]


def parse_api_time(time: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(time)


def format_api_time(time: datetime.datetime):
    return time.isoformat("T").replace("+00:00", "Z")


def nuke_key(d: dict, key: str) -> None:
    try:
        del d[key]
    except KeyError:
        pass


KitsunekkoId = typing.NewType("KitsunekkoId", int)
AnilistId = typing.NewType("AnilistId", int)
TMDBId = typing.NewType("TMDBId", str)  # example: "tv:153496"


@dataclasses.dataclass(frozen=True)
class ApiDirectoryEntry(DirectoryMetaProtocol):
    entry_id: KitsunekkoId  # used to query API for files in the directory
    name: str  # name of the anime and the directory on the disk.
    entry_type: EntryType
    last_modified: datetime.datetime  # format RFC3339: '2024-04-27T17:54:01Z'
    english_name: str | None = None
    japanese_name: str | None = None
    anilist_id: AnilistId | None = None
    tmdb_id: TMDBId | None = None

    def is_anime(self) -> bool:
        return self.entry_type in (EntryType.anime_tv, EntryType.anime_movie)

    def is_drama(self) -> bool:
        return self.entry_type in (EntryType.drama_tv, EntryType.drama_movie)

    @property
    def fs_name(self) -> str:
        return fs_name_strip(self.name)

    @classmethod
    def from_api_json(cls, json_dict: ApiDirectoryDict) -> typing.Self:
        """
        Construct self from the API JSON response.
        """
        return cls(
            entry_id=KitsunekkoId(json_dict["id"]),
            name=json_dict["name"].strip(),
            entry_type=describe_entry_type(json_dict["flags"]),
            last_modified=parse_api_time(json_dict["last_modified"]),
            english_name=json_dict.get("english_name", "").strip(),
            japanese_name=json_dict.get("japanese_name", "").strip(),
            anilist_id=AnilistId(json_dict["anilist_id"]) if "anilist_id" in json_dict else None,
            tmdb_id=TMDBId(json_dict["tmdb_id"]) if "tmdb_id" in json_dict else None,
        )

    def write_to_file(self, fp: typing.TextIO) -> None:
        """
        Format self and store on disk.
        The schema differs a bit from what the program receives from the remote server.
        """
        as_dict = dataclasses.asdict(self)
        as_dict["last_modified"] = format_api_time(self.last_modified)
        as_dict["entry_type"] = self.entry_type.name
        nuke_key(as_dict, "dir_path")  # no need to store this on disk
        json.dump(
            {k: v for k, v in as_dict.items() if v},
            fp,
            indent=2,
            ensure_ascii=False,
        )

    def with_mod_time(self, mod_time: datetime.datetime) -> typing.Self:
        return dataclasses.replace(self, last_modified=mod_time)


def iter_catalog_directories(json_response: Sequence[ApiDirectoryDict]) -> typing.Iterable[ApiDirectoryEntry]:
    for item in json_response:
        yield ApiDirectoryEntry.from_api_json(item)


def get_meta_file_path_on_disk(parent_dir: pathlib.Path) -> pathlib.Path:
    """
    Return path to .kitsuinfo.json in this directory.
    """
    return parent_dir.joinpath(INFO_FILENAME)


def destination_for_dir(remote_dir: ApiDirectoryEntry, config: KitsuConfig) -> pathlib.Path:
    return config.destination / remote_dir.entry_type.name


def get_meta_file_path(remote_dir: ApiDirectoryEntry, config: KitsuConfig) -> pathlib.Path:
    return get_meta_file_path_on_disk(parent_dir=destination_for_dir(remote_dir, config).joinpath(remote_dir.fs_name))


def main() -> None:
    example = {
        "id": 923,
        "name": "Yuru Yuri Nachuyachumi!",
        "flags": {"anime": True, "low_quality": False, "external": True, "movie": False, "adult": False},
        "last_modified": "2024-04-12T02:52:11Z",
        "anilist_id": 20625,
        "english_name": "YuruYuri Nachuyachumi!",
        "japanese_name": "ゆるゆり\u3000なちゅやちゅみ！",
    }
    pprint(ApiDirectoryEntry.from_api_json(example), indent=2)
    example = {
        "id": 3153,
        "name": "Wild Heroes",
        "flags": {"anime": False, "low_quality": False, "external": False, "movie": False, "adult": False},
        "last_modified": "2024-04-18T19:20:14Z",
        "creator_id": 1,
        "tmdb_id": "tv:86984",
        "english_name": "Wild Heroes",
        "japanese_name": "ワイルド・ヒーローズ",
    }
    pprint(ApiDirectoryEntry.from_api_json(example), indent=2)


if __name__ == "__main__":
    main()
