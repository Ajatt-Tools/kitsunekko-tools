# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

import pytest

from kitsunekko_tools.consts import FALLBACK_MIME_TYPE
from kitsunekko_tools.ignore import FileMetaData
from kitsunekko_tools.website.templates import mime_type_filter
from kitsunekko_tools.website.website import (
    LocalDirectoryEntry,
    catalog_file_sort_key,
    collect_sitemap_urls,
    entry_sort_key,
)
from tests.helpers import make_paths, mk_entry, mk_file, year


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


@pytest.mark.parametrize(
    "entries, url_len",
    [
        (
            [],
            2,
        ),
        (
            [
                mk_entry(name="My Show", year_=2024),
            ],
            3,
        ),
        (
            [
                mk_entry(name="Orphan Dir", has_meta=False),
            ],
            3,
        ),
        (
            [mk_entry(name=f"Show {i}", year_=2024) for i in range(5)],
            7,
        ),
    ],
    ids=["empty", "one show", "orphan", "many"],
)
def test_collect_sitemap_urls_index_pages_use_build_date(
    tmp_path: pathlib.Path, entries: list[LocalDirectoryEntry], url_len: int
) -> None:
    """
    Index pages always receive the build date, not an entry date.
    Entry pages with metadata use the entry's own last_modified date.
    Entry pages without metadata fall back to the build date.
    Total URL count equals 2 index pages plus number of entries.
    """
    paths = make_paths(tmp_path)
    build_date = year(2026)
    urls = collect_sitemap_urls(entries, paths, build_date)
    assert len(urls) == url_len
    assert all(u.last_modified == build_date for u in urls[:2])
    assert urls[0].file_path == paths.index_file_path
    assert urls[1].file_path == paths.drama_index_file_path
    for collected, reference in zip(urls[2:], entries):
        assert collected.file_path == reference.site_path_to_html_file
        if reference.meta is not None:
            assert collected.last_modified == reference.meta.last_modified
        else:
            assert collected.last_modified == build_date
