# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import json
import typing


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


@dataclasses.dataclass
class ApiDirectory:
    entry_id: int  # used to query API for files in the directory
    name: str
    entry_type: str
    last_modified: str  # format RFC3339: '2024-04-27T17:54:01Z'
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
            entry_id=json_dict["id"],
            name=json_dict["name"],
            entry_type=describe_entry_type(json_dict["flags"]),
            last_modified=json_dict["last_modified"],
            english_name=json_dict.get("english_name"),
            japanese_name=json_dict.get("japanese_name"),
            anilist_id=json_dict.get("anilist_id"),
            tmdb_id=json_dict.get("tmdb_id"),
        )

    def pack_kitsu_json(self) -> str:
        """
        Format self for storing on disk.
        The schema differs a bit from what the program receives from the remote server.
        """
        return json.dumps(
            {k: v for k, v in dataclasses.asdict(self).items() if v is not None},
            indent=2,
            ensure_ascii=False,
        )


def iter_catalog_directories(json_response: list[ApiDirectoryDict]) -> typing.Iterable[ApiDirectory]:
    for item in json_response:
        yield ApiDirectory.from_api_json(item)


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
    print(ApiDirectory.from_api_json(example).pack_kitsu_json())
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
    print(ApiDirectory.from_api_json(example).pack_kitsu_json())


if __name__ == "__main__":
    main()
