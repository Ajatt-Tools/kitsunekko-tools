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


class ApiDirectoryFlagsDict(typing.TypedDict):
    adult: bool
    anime: bool
    external: bool
    low_quality: bool
    movie: bool


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


def describe_entry_type(flags: ApiDirectoryFlagsDict) -> str:
    return f'{"anime" if flags["anime"] else "drama"}_{"movie" if flags["movie"] else "tv"}'


def parse_api_time(time: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(time)


def format_api_time(time: datetime.datetime):
    return time.isoformat("T").replace("+00:00", "Z")


def nuke_key(d: dict, key: str) -> None:
    try:
        del d[key]
    except KeyError:
        pass


EntryId = typing.NewType("EntryId", int)


@dataclasses.dataclass(frozen=True)
class ApiDirectoryEntry:
    entry_id: EntryId  # used to query API for files in the directory
    name: str  # name of the anime and the directory on the disk.
    entry_type: str
    last_modified: datetime.datetime  # format RFC3339: '2024-04-27T17:54:01Z'
    english_name: str | None = None
    japanese_name: str | None = None
    anilist_id: int | None = None
    tmdb_id: str | None = None

    @classmethod
    def from_api_json(cls, json_dict: ApiDirectoryDict) -> typing.Self:
        """
        Construct self from the API json response.
        """
        return cls(
            entry_id=EntryId(json_dict["id"]),
            name=fs_name_strip(json_dict["name"]),
            entry_type=describe_entry_type(json_dict["flags"]),
            last_modified=parse_api_time(json_dict["last_modified"]),
            english_name=json_dict.get("english_name", "").strip(),
            japanese_name=json_dict.get("japanese_name", "").strip(),
            anilist_id=json_dict.get("anilist_id"),
            tmdb_id=json_dict.get("tmdb_id"),
        )

    def write_to_file(self, fp: typing.TextIO) -> None:
        """
        Format self and store on disk.
        The schema differs a bit from what the program receives from the remote server.
        """
        as_dict = dataclasses.asdict(self)
        as_dict["last_modified"] = format_api_time(self.last_modified)
        nuke_key(as_dict, "dir_path")  # no need to store this on disk
        json.dump(
            {k: v for k, v in as_dict.items() if v},
            fp,
            indent=2,
            ensure_ascii=False,
        )


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
        return data


def iter_catalog_directories(json_response: Sequence[ApiDirectoryDict]) -> typing.Iterable[ApiDirectoryEntry]:
    for item in json_response:
        yield ApiDirectoryEntry.from_api_json(item)


def main():
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
