# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import datetime
import pathlib
from collections.abc import Sequence

import pytest

from kitsunekko_tools.consts import KITSUNEKKO_DOMAIN_URL
from kitsunekko_tools.scrapper.parse import (
    AnimeDir,
    SubtitleFile,
    find_all_subtitle_dirs,
    find_all_subtitle_files,
)

DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")
EXPECTED_DIRS = [
    AnimeDir(
        f"{KITSUNEKKO_DOMAIN_URL}/dirlist.php?dir=subtitles%2Fjapanese%2FYuru+Camp+S3%2F",
        "Yuru Camp S3",
        datetime.datetime(2024, 4, 25, 19, 38, 39),
    ),
    AnimeDir(
        f"{KITSUNEKKO_DOMAIN_URL}/dirlist.php?dir=subtitles%2Fjapanese%2FSousou+no+Frieren%2F",
        "Sousou no Frieren",
        datetime.datetime(2024, 4, 14, 18, 23, 19),
    ),
]

EXPECTED_FILES = [
    SubtitleFile(
        url=f"{KITSUNEKKO_DOMAIN_URL}/subtitles/japanese/Hibike! Euphonium/[Kamigami] Hibike! Euphonium - 13 [1280x720 x264 AAC Sub(Chs,Cht,Jap)].ass",
        show_name="Hibike! Euphonium",
        file_name="[Kamigami] Hibike! Euphonium - 13 [1280x720 x264 AAC Sub(Chs,Cht,Jap)].ass",
        mod_timestamp=datetime.datetime(2015, 7, 3, 14, 48, 34),
    ),
    SubtitleFile(
        url=f"{KITSUNEKKO_DOMAIN_URL}/subtitles/japanese/Hibike! Euphonium/[Kamigami] Hibike! Euphonium - 14 (BDRip 1280x720 AVC 10bit FLAC).JP.ass",
        show_name="Hibike! Euphonium",
        file_name="[Kamigami] Hibike! Euphonium - 14 (BDRip 1280x720 AVC 10bit FLAC).JP.ass",
        mod_timestamp=datetime.datetime(2016, 2, 21, 19, 30, 12),
    ),
]


@pytest.fixture
def found_dirs() -> Sequence[AnimeDir]:
    root_html_text = DATA_DIR.joinpath("main_dir_page.html").read_text()
    return [*find_all_subtitle_dirs(root_html_text)]


@pytest.fixture
def parsed_sub_files() -> Sequence[SubtitleFile]:
    anime_dir_html_text = DATA_DIR.joinpath("subs_page.html").read_text()
    return [*find_all_subtitle_files(anime_dir_html_text)]


def test_shows_in_root_dir(found_dirs: Sequence[AnimeDir]) -> None:
    assert all(dir_ in found_dirs for dir_ in EXPECTED_DIRS), "result should include expected dirs"


def test_num_of_found_dirs(found_dirs: Sequence[AnimeDir]) -> None:
    assert len(found_dirs) == 2653, "number of directories should match"


def test_files_in_directory(parsed_sub_files: Sequence[SubtitleFile]) -> None:
    assert all(file in parsed_sub_files for file in EXPECTED_FILES), "result should include expected files"


def test_num_of_found_files(parsed_sub_files: Sequence[SubtitleFile]) -> None:
    assert len(parsed_sub_files) == 67, "number of files should match"
