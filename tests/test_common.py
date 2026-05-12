# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import pathlib
import random

import pytest

from kitsunekko_tools.common import datetime_now_utc, max_datetime
from kitsunekko_tools.ignore import IgnoreFileEntry, ignore_pattern_sort_key
from kitsunekko_tools.scrapper.dir_path_matcher import (
    local_dir_sort_key,
    name_strip_insignificant_chars,
)
from tests.helpers import (
    OSHI_NO_KO_IGNORE_LIST_SORTED,
    mk_ignore_entry,
    mk_kitsu_meta,
    mk_no_meta,
    year,
)

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
