# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import pathlib
import random

import pytest

from kitsunekko_tools.api_access.root_directory import KitsunekkoId, parse_api_time
from kitsunekko_tools.common import datetime_now_utc, max_datetime
from kitsunekko_tools.entry import EntryType
from kitsunekko_tools.ignore import IgnoreFileEntry, ignore_pattern_sort_key
from kitsunekko_tools.local_state import KitsuDirectoryMeta
from kitsunekko_tools.scrapper.dir_path_matcher import (
    local_dir_sort_key,
    name_strip_insignificant_chars,
)
from kitsunekko_tools.scrapper.types import NoMetaDirectoryEntry

NOW = datetime_now_utc()


@pytest.mark.parametrize(
    "t1, t2,  expectation",
    [
        (year(2003), year(2025), year(2025)),
        (year(2023), year(2021), year(2023)),
        (year(2003), year(2999), NOW),
    ],
)
def test_max_datetime(t1: datetime.datetime, t2: datetime.datetime, expectation: datetime.datetime) -> None:
    result = max_datetime(t1, t2)
    assert result.year == expectation.year


@pytest.mark.parametrize(
    "s1, s2",
    [
        ("Yu☆Gi☆Oh! ARC-V", "Yu-Gi-Oh! ARC-V"),
        ("Yu-Gi-Oh! ZEXAL", "Yu☆Gi☆Oh! ZEXAL"),
    ],
)
def test_name_strip_insignificant_chars(s1: str, s2: str) -> None:
    assert name_strip_insignificant_chars(s1) == name_strip_insignificant_chars(s2)


def mk_real_ignore_entry(*, name: str, st_size: int, last_modified: str) -> IgnoreFileEntry:
    """Create an IgnoreFileEntry from real API data."""
    return IgnoreFileEntry(name=name, last_modified=parse_api_time(last_modified), st_size=st_size)


# A subset of a real ignore list, already in expected sorted order.
OSHI_NO_KO_IGNORE_LIST_SORTED = [
    mk_real_ignore_entry(
        name="OSHI.NO.KO.S03E01.1080p.NF.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.srt",
        st_size=32664,
        last_modified="2026-01-15T22:56:46.590728Z",
    ),
    mk_real_ignore_entry(
        name="[NanakoRaws] Oshi no Ko - S03E05 (TV 1920x1080 x265 AAC).ass",
        st_size=68084,
        last_modified="2026-03-07T15:23:30.954202Z",
    ),
    mk_real_ignore_entry(
        name="[NanakoRaws] Oshi no Ko - S03E05 (TV 1920x1080 x265 AAC).srt",
        st_size=30602,
        last_modified="2026-03-07T15:23:30.954202Z",
    ),
    mk_real_ignore_entry(
        name="[NanakoRaws] Oshi no Ko S3 - 01 (AT-X 1920x1080 x265 AAC).ass",
        st_size=67637,
        last_modified="2026-01-16T16:43:28.550094Z",
    ),
    mk_real_ignore_entry(
        name="[SubsPlease] Oshi no Ko S3 - 01 (1080p) [8E2B58B0].jpn.ass",
        st_size=67634,
        last_modified="2026-02-09T13:24:41.792165Z",
    ),
    mk_real_ignore_entry(
        name="[shincaps] Oshi no Ko 3rd Season - 01 (AT-X 1440x1080 MPEG2 AAC).ass",
        st_size=68183,
        last_modified="2026-01-15T13:50:46.714913Z",
    ),
    mk_real_ignore_entry(
        name="[shincaps] Oshi no Ko 3rd Season - 01 (AT-X 1440x1080 MPEG2 AAC).srt",
        st_size=31070,
        last_modified="2026-01-15T13:50:46.714913Z",
    ),
    mk_real_ignore_entry(
        name="【OSHI NO KO】 S03E35 Episode 35 Japanese [CC].srt",
        st_size=32914,
        last_modified="2026-01-15T22:56:38.470710Z",
    ),
    mk_real_ignore_entry(
        name="【推しの子】.S03E03.第27話.コンプライアンス.WEBRip.Amazon.ja-jp[sdh].srt",
        st_size=84900,
        last_modified="2026-03-28T05:54:16.930450Z",
    ),
    mk_real_ignore_entry(
        name="【推しの子】.S03E26.打算.WEBRip.Netflix.ja[cc].srt",
        st_size=31099,
        last_modified="2026-04-02T01:21:28.410030Z",
    ),
]


@pytest.mark.parametrize(
    "entries, expected_order",
    [
        (
            [mk_ignore_entry(name="beta.srt"), mk_ignore_entry(name="alpha.srt")],
            [mk_ignore_entry(name="alpha.srt"), mk_ignore_entry(name="beta.srt")],
        ),
        (
            [mk_ignore_entry(name="same.srt", st_size=200), mk_ignore_entry(name="same.srt", st_size=100)],
            [mk_ignore_entry(name="same.srt", st_size=100), mk_ignore_entry(name="same.srt", st_size=200)],
        ),
        (
            [mk_ignore_entry(name="same.srt", year_=2025), mk_ignore_entry(name="same.srt", year_=2023)],
            [mk_ignore_entry(name="same.srt", year_=2023), mk_ignore_entry(name="same.srt", year_=2025)],
        ),
        (
            # Shuffled entries from a real ignore list example.
            random.sample(OSHI_NO_KO_IGNORE_LIST_SORTED, k=len(OSHI_NO_KO_IGNORE_LIST_SORTED)),
            OSHI_NO_KO_IGNORE_LIST_SORTED,
        ),
    ],
    ids=["by_name", "by_size", "by_date", "realistic_ignore_list"],
)
def test_pattern_sort_key(entries: list[IgnoreFileEntry], expected_order: list) -> None:
    result = sorted(entries, key=ignore_pattern_sort_key)
    assert result == expected_order


@pytest.mark.parametrize(
    "entries, expected_best_name",
    [
        (
            [mk_no_meta(name="No Meta", year_=2025), mk_kitsu_meta(name="Has Meta", year_=2020)],
            "Has Meta",
        ),
        (
            [mk_kitsu_meta(name="Older Show", year_=2020), mk_kitsu_meta(name="Newer Show", year_=2025)],
            "Newer Show",
        ),
        (
            [mk_no_meta(name="Older Orphan", year_=2020), mk_no_meta(name="Newer Orphan", year_=2025)],
            "Newer Orphan",
        ),
    ],
    ids=["meta_over_no_meta", "newer_meta_wins", "newer_no_meta_wins"],
)
def test_local_dir_sort_key(entries: list, expected_best_name: str) -> None:
    best = max(entries, key=local_dir_sort_key)
    assert best.name == expected_best_name
