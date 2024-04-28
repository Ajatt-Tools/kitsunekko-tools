# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import datetime
import pathlib

from kitsunekko_tools.consts import KITSUNEKKO_DOMAIN_URL
from kitsunekko_tools.kitsunekko import AnimeDir, SubtitleFile, find_all_subtitle_dirs, find_all_subtitle_files

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


def test_root_dir_parser():
    root_html_text = DATA_DIR.joinpath("main_dir_page.html").read_text()
    parsed = [*find_all_subtitle_dirs(root_html_text)]
    assert all(directory in parsed for directory in EXPECTED_DIRS)


def test_anime_dir_parser():
    anime_dir_html_text = DATA_DIR.joinpath("subs_page.html").read_text()
    parsed = [*find_all_subtitle_files(anime_dir_html_text)]
    assert all(file in parsed for file in EXPECTED_FILES)
