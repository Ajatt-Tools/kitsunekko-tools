# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import typing

from kitsunekko_tools.common import fs_name_strip


class ApiFileDict(typing.TypedDict):
    url: str
    name: str
    size: int
    last_modified: str


@dataclasses.dataclass(frozen=True)
class ApiFileEntry:
    url: str
    name: str
    size: int  # The file's size in bytes.
    last_modified: str  # Modification time in UTC, e.g. "2024-04-01T07:57:39.541025942Z"

    @classmethod
    def from_api_json(cls, json_dict: ApiFileDict):
        return cls(**(json_dict | {"name": fs_name_strip(json_dict["name"])}))


def iter_directory_files(json_response: typing.Sequence[ApiFileDict]) -> typing.Iterable[ApiFileEntry]:
    for item in json_response:
        yield ApiFileEntry.from_api_json(item)


def main():
    example = {
        "url": "https://kitsunekko.net/entry/1049/download/Cherry%20Maho%20-%2008%20(TX%201920x1080%20x264%20AAC).srt",
        "name": "Cherry Maho - 08 (TX 1920x1080 x264 AAC).srt",
        "size": 29464,
        "last_modified": "2024-03-03T11:53:18Z",
    }
    print(ApiFileEntry.from_api_json(example))


if __name__ == "__main__":
    main()
