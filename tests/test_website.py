# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import pathlib
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from typing import NamedTuple

import pytest

from kitsunekko_tools.common import join_url
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import (
    ARCHIVE_FILE_TYPES,
    FALLBACK_MIME_TYPE,
    SITEMAP_NS,
    SUBTITLE_FILE_TYPES,
)
from kitsunekko_tools.entry import EntryType
from kitsunekko_tools.ignore import FileMetaData
from kitsunekko_tools.website.templates import mime_type_filter
from kitsunekko_tools.website.website import (
    LocalDirectoryEntry,
    WebSiteBuilder,
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
        (
            [mk_entry(name="Zebra Show", year_=2024), mk_entry(name="Alpha Show", year_=2024)],
            "Alpha Show",
        ),
    ],
    ids=["newest_first", "meta_before_no_meta", "no_meta_alphabetical", "same_timestamp_alphabetical"],
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
        (
            [
                mk_file(name="old_trash.srt", year_=2020, trashed=True),
                mk_file(name="new_trash.srt", year_=2025, trashed=True),
            ],
            [
                mk_file(name="new_trash.srt", year_=2025, trashed=True),
                mk_file(name="old_trash.srt", year_=2020, trashed=True),
            ],
        ),
    ],
    ids=["trashed_last", "newest_first", "size_tiebreaker", "trashed_newest_first"],
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


@pytest.fixture
def tmp_site_builder(tmp_path: pathlib.Path) -> WebSiteBuilder:
    """Create a WebSiteBuilder with a temporary directory structure."""
    # Create directory structure
    dest = tmp_path / "subtitles"
    dest.mkdir()
    for entry_type in EntryType:
        dest.joinpath(entry_type.name).mkdir()

    config = KitsuConfig(
        destination=dest,
        skip_older=datetime.timedelta(days=30),
        allowed_file_types=frozenset([*SUBTITLE_FILE_TYPES, *ARCHIVE_FILE_TYPES]),
    )

    builder = WebSiteBuilder(config)
    builder._paths.site_dir_path.mkdir(parents=True, exist_ok=True)
    builder.copy_site_resources()

    return builder


def mk_site_entry(
    builder: WebSiteBuilder, *, name: str, year_: int = 2024, has_meta: bool = True
) -> LocalDirectoryEntry:
    """Create a LocalDirectoryEntry with a path inside the site directory."""
    entry = mk_entry(name=name, year_=year_, has_meta=has_meta)
    # Override site_path_to_html_file to be inside the actual site directory.
    site_path = builder._paths.site_dir_path / "anime_tv" / f"{name.lower().replace(' ', '-')}.html"
    site_path.parent.mkdir(parents=True, exist_ok=True)
    return LocalDirectoryEntry(
        meta=entry.meta,
        path_to_dir=entry.path_to_dir,
        files_in_dir=entry.files_in_dir,
        site_path_to_html_file=site_path,
        is_drama=entry.is_drama,
    )


def test_generate_robots_txt_creates_file(tmp_site_builder: WebSiteBuilder) -> None:
    """Verify robots.txt is created with correct content."""
    tmp_site_builder.generate_robots_txt()
    robots_path = tmp_site_builder._paths.robots_file_path

    assert robots_path.exists()
    content = robots_path.read_text(encoding="utf-8")
    assert content.startswith("User-agent: *\nAllow: /\n")
    assert "Sitemap:" in content


class EntrySpec(NamedTuple):
    """Lightweight specification for a sitemap test entry."""

    name: str
    has_meta: bool = True


def _generate_sitemap_content(tmp_site_builder: WebSiteBuilder, entries_spec: Sequence[EntrySpec]) -> str:
    """Generate a sitemap and return its text content."""
    entries = [
        mk_site_entry(tmp_site_builder, name=spec.name, year_=2024, has_meta=spec.has_meta) for spec in entries_spec
    ]
    tmp_site_builder.generate_sitemap(entries)
    sitemap_path = tmp_site_builder._paths.sitemap_file_path
    assert sitemap_path.exists()
    return sitemap_path.read_text(encoding="utf-8")


def _ns(tag: str) -> str:
    return f"{{{SITEMAP_NS}}}{tag}"


def _sitemap_locs(root: ET.Element) -> list[str]:
    """Extract all <loc> text from a sitemap root element."""
    return [str(loc.text) for url_elem in root for loc in url_elem if loc.tag == _ns("loc") and loc.text]


def _sitemap_filenames(root: ET.Element) -> list[str]:
    """Extract all filenames from <loc> elements."""
    return [pathlib.Path(x).name for x in _sitemap_locs(root)]


ALWAYS_PRESENT = frozenset(["index.html", "drama.html"])


@pytest.mark.parametrize(
    "entries_spec, expected_substrings",
    [
        ([], ["index.html", "drama.html"]),
        ([EntrySpec("My Show")], ["my-show.html"]),
        ([EntrySpec("Another Show")], ["another-show.html"]),
        ([EntrySpec("My Show"), EntrySpec("Another Show")], ["my-show.html", "another-show.html"]),
        ([EntrySpec("Orphan", has_meta=False)], ["orphan.html"]),
    ],
    ids=["index_pages", "entry_my_show", "entry_another_show", "both_entries", "orphan_entry"],
)
def test_sitemap_page_presence(
    tmp_site_builder: WebSiteBuilder,
    entries_spec: list[EntrySpec],
    expected_substrings: list[str],
) -> None:
    """Verify that expected URLs appear in the sitemap's <loc> elements."""
    content = _generate_sitemap_content(tmp_site_builder, entries_spec)
    root = ET.fromstring(content)
    assert ALWAYS_PRESENT.union(expected_substrings) == frozenset(_sitemap_filenames(root))


def test_sitemap_excludes_not_found(tmp_site_builder: WebSiteBuilder) -> None:
    """Verify not_found.html is NOT in the sitemap."""
    content = _generate_sitemap_content(tmp_site_builder, ())
    root = ET.fromstring(content)
    assert "not_found.html" not in _sitemap_filenames(root)


@pytest.mark.parametrize(
    "entry_spec",
    [
        EntrySpec("Test Show"),
        EntrySpec("Orphan", has_meta=False),
    ],
    ids=["with_meta", "orphan"],
)
def test_sitemap_structure(tmp_site_builder: WebSiteBuilder, entry_spec: EntrySpec) -> None:
    """Parse the sitemap as XML and validate protocol compliance."""
    content = _generate_sitemap_content(tmp_site_builder, (entry_spec,))

    root = ET.fromstring(content)

    assert root.tag == _ns("urlset")
    assert len(root) > 0

    for url_elem in root:
        assert url_elem.tag == _ns("url")

        locs = [c for c in url_elem if c.tag == _ns("loc")]
        assert len(locs) == 1, f"<url> must have exactly one <loc>, found {len(locs)}"
        loc = locs[0]
        assert loc.text, "<loc> must be non-empty"
        assert loc.text.startswith("https://"), f"<loc> must be https: {loc.text}"

        lastmods = [c for c in url_elem if c.tag == _ns("lastmod")]
        assert len(lastmods) == 1, f"<url> must have exactly one <lastmod>, found {len(lastmods)}"
        lastmod = lastmods[0]
        assert lastmod.text, "<lastmod> must be non-empty"
        assert datetime.date.fromisoformat(lastmod.text).year > 2000


@pytest.mark.parametrize(
    "parts, expected",
    [
        (("https://ajatt.top/blog/", "page.html"), "https://ajatt.top/blog/page.html"),
        (("https://ajatt.top/blog", "page.html"), "https://ajatt.top/blog/page.html"),
        (("https://ajatt.top/blog/", "/page.html"), "https://ajatt.top/blog/page.html"),
        (("https://ajatt.top/blog", "res/blog.css"), "https://ajatt.top/blog/res/blog.css"),
        (("https://ajatt.top/blog", "res", "blog.css"), "https://ajatt.top/blog/res/blog.css"),
        (("https://ajatt.top/blog/",), "https://ajatt.top/blog"),
        ((), ""),
    ],
    ids=[
        "trailing_slash",
        "no_trailing_slash",
        "leading_slash",
        "path_segments_joined",
        "path_segments",
        "single_part",
        "empty",
    ],
)
def test_join_url(parts: tuple[str, ...], expected: str) -> None:
    assert join_url(*parts) == expected
