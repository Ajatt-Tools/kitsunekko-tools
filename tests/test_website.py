# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import pathlib

import pytest

from kitsunekko_tools.api_access.root_directory import KitsunekkoId
from kitsunekko_tools.entry import EntryType
from kitsunekko_tools.ignore import FileMetaData
from kitsunekko_tools.local_state import KitsuDirectoryMeta
from kitsunekko_tools.website.website import (
    LocalDirectoryEntry,
    catalog_file_sort_key,
    entry_sort_key,
)
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


def mk_file(*, name: str, year_: int = 2024, st_size: int = 100, trashed: bool = False) -> FileMetaData:
    """Create a FileMetaData for testing."""
    parent = pathlib.Path("/tmp/extra") if trashed else pathlib.Path("/tmp/subs")
    return FileMetaData(
        name=name,
        last_modified=year(year_),
        st_size=st_size,
        path=parent / name,
    )


@pytest.mark.parametrize(
    "entries, expected_first_name",
    [
        (
            [mk_entry(name="Older Show", year_=2020), mk_entry(name="Newer Show", year_=2025)],
            "Newer Show",
        ),
        (
            [mk_entry(name="No Meta Dir", has_meta=False), mk_entry(name="Has Meta", year_=2024)],
            "Has Meta",
        ),
        (
            [mk_entry(name="Zeta Dir", has_meta=False), mk_entry(name="Alpha Dir", has_meta=False)],
            "Alpha Dir",
        ),
    ],
    ids=["newest_first", "meta_before_no_meta", "no_meta_alphabetical"],
)
def test_entry_sort_key(entries: list[LocalDirectoryEntry], expected_first_name: str) -> None:
    result = sorted(entries, key=entry_sort_key)
    first = result[0]
    actual_name = first.meta.name if first.meta else first.path_to_dir.name
    assert actual_name == expected_first_name


@pytest.mark.parametrize(
    "files, expected",
    [
        (
            [mk_file(name="trashed.srt", trashed=True), mk_file(name="active.srt", trashed=False)],
            [mk_file(name="active.srt", trashed=False), mk_file(name="trashed.srt", trashed=True)],
        ),
        (
            [mk_file(name="old.srt", year_=2020), mk_file(name="new.srt", year_=2025)],
            [mk_file(name="new.srt", year_=2025), mk_file(name="old.srt", year_=2020)],
        ),
        (
            [mk_file(name="big.srt", st_size=500), mk_file(name="big.srt", st_size=100)],
            [mk_file(name="big.srt", st_size=100), mk_file(name="big.srt", st_size=500)],
        ),
    ],
    ids=["trashed_last", "newest_first", "size_tiebreaker"],
)
def test_catalog_file_sort_key(files: list[FileMetaData], expected: list[FileMetaData]) -> None:
    result = sorted(files, key=catalog_file_sort_key)
    assert result == expected


@pytest.mark.parametrize(
    "files, expected_sizes",
    [
        (
            [mk_file(name="big.srt", st_size=500), mk_file(name="big.srt", st_size=100)],
            [100, 500],
        ),
    ],
    ids=["size_ascending"],
)
def test_catalog_file_sort_key_size_order(files: list[FileMetaData], expected_sizes: list[int]) -> None:
    result = sorted(files, key=catalog_file_sort_key)
    assert [f.st_size for f in result] == expected_sizes
