# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import json
import pathlib
from collections.abc import Sequence

import pytest

from kitsunekko_tools.api_access.directory_entry import read_meta_file
from kitsunekko_tools.api_access.root_directory import (
    ApiDirectoryDict,
    ApiDirectoryEntry,
    iter_catalog_directories,
)
from kitsunekko_tools.consts import BUNDLED_SUBTITLES_DIR, INFO_FILENAME
from kitsunekko_tools.local_state import KitsuDirectoryMeta
from kitsunekko_tools.sanitize import DuplicatesGroup
from tests.test_parser import DATA_DIR


@pytest.fixture(params=["entries_search_anime_response.json", "entries_search_dramas_response.json"])
def search_response_json(request) -> Sequence[ApiDirectoryDict]:
    with open(DATA_DIR.joinpath(request.param), encoding="utf-8") as f:
        return json.load(f)


def test_shows_in_root_dir(search_response_json: Sequence[ApiDirectoryDict]) -> None:
    dirs: list[ApiDirectoryEntry] = [*iter_catalog_directories(search_response_json)]
    assert len(dirs) > 0
    assert all(dir_.entry_id > 0 for dir_ in dirs)
    assert all(dir_.name for dir_ in dirs)
    date_threshold = datetime.datetime.fromisoformat("2012-07-15 20:21:54+00:00")
    assert all(dir_.last_modified > date_threshold for dir_ in dirs)


def collect_meta(subtitles_dir: pathlib.Path) -> list[KitsuDirectoryMeta]:
    return [read_meta_file(meta_file_path) for meta_file_path in subtitles_dir.rglob(INFO_FILENAME)]


@pytest.mark.parametrize(
    "entries,  original_name",
    [
        (collect_meta(BUNDLED_SUBTITLES_DIR / "anime_tv"), "[Oshi no Ko] 3rd Season"),
        (collect_meta(BUNDLED_SUBTITLES_DIR / "drama_tv"), "Setsuen Chase"),
    ],
)
def test_dir_meta_sort_key(entries: list[KitsuDirectoryMeta], original_name: str) -> None:
    group = DuplicatesGroup.from_list(entries)
    assert group.original.name == original_name


@pytest.mark.parametrize(
    "input_string, expected_count",
    [
        ("Setsuen Chase", 12),
        ("雪煙チェイス", 0),
        ("SPY×FAMILY", 9),
        ("", 0),
        ("abc123XYZ", 6),
    ],
)
def test_count_ascii_letters(input_string: str, expected_count: int) -> None:
    assert count_ascii_letters(input_string) == expected_count


@pytest.mark.parametrize(
    "entries, expected_first_id",
    [
        # Newer timestamp wins.
        (
            [
                make_api_entry(entry_id=1, last_modified=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC)),
                make_api_entry(entry_id=2, last_modified=datetime.datetime(2026, 1, 4, tzinfo=datetime.UTC)),
                make_api_entry(entry_id=3, last_modified=datetime.datetime(2026, 1, 7, tzinfo=datetime.UTC)),
                make_api_entry(entry_id=4, last_modified=datetime.datetime(2026, 1, 12, tzinfo=datetime.UTC)),
                make_api_entry(entry_id=5, last_modified=datetime.datetime(2026, 1, 6, tzinfo=datetime.UTC)),
            ],
            4,
        ),
        # Same timestamp, more ASCII letters wins.
        (
            [
                make_api_entry(entry_id=1, name="MoreASCII"),
                make_api_entry(entry_id=2, name="日本語"),
                make_api_entry(entry_id=3, name="nihongo title"),
                make_api_entry(entry_id=4, name="片言"),
            ],
            3,
        ),
    ],
)
def test_dir_meta_sort_key_ordering(
    entries: Sequence[KitsuDirectoryMeta],
    expected_first_id: int,
) -> None:
    sorted_entries = sorted(entries, key=dir_meta_sort_key)
    assert sorted_entries[0].entry_id == expected_first_id


