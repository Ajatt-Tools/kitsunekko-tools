# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import pathlib

import pytest

from kitsunekko_tools.consts import FALLBACK_MIME_TYPE
from kitsunekko_tools.ignore import FileMetaData
from kitsunekko_tools.website.templates import mime_type_filter
from kitsunekko_tools.website.website import (
    LocalDirectoryEntry,
    catalog_file_sort_key,
    entry_sort_key,
)
from tests.helpers import mk_entry, mk_file


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


@pytest.mark.parametrize(
    "path, expected",
    [
        ("logo.webp", "image/webp"),
        ("index.html", "text/html"),
        ("style.css", "text/css"),
        (pathlib.Path("/some/dir/logo.webp"), "image/webp"),
        ("file.unknownext", FALLBACK_MIME_TYPE),
        ("no_extension", FALLBACK_MIME_TYPE),
        ("", FALLBACK_MIME_TYPE),
    ],
    ids=["webp", "html", "css", "path_obj", "unknown_ext", "no_ext", "empty"],
)
def test_mime_type_filter(path: pathlib.Path | str, expected: str) -> None:
    assert mime_type_filter(path) == expected
