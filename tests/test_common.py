# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime

import pytest

from kitsunekko_tools.common import datetime_now_utc, max_datetime
from kitsunekko_tools.scrapper.dir_path_matcher import name_strip_insignificant_chars

NOW = datetime_now_utc()


def year(year_: int) -> datetime.datetime:
    return datetime.datetime(year=year_, month=1, day=1, tzinfo=datetime.UTC)


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
