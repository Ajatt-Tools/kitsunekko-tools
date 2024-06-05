# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import datetime
import itertools
import pathlib
import re
import typing
import urllib.parse

from kitsunekko_tools.common import fs_name_strip
from kitsunekko_tools.consts import KITSUNEKKO_DOMAIN_URL
from kitsunekko_tools.scrapper.types import AnimeDir, SubtitleFile

MOD_TIMESTAMP_FORMAT = "%b %d %Y %I:%M:%S %p"  # timestamp format used on kitsunekko


def datetime_from_str(mod_timestamp: str) -> datetime.datetime:
    return datetime.datetime.strptime(mod_timestamp, MOD_TIMESTAMP_FORMAT)


RE_FLAGS = re.IGNORECASE

# <tr><td colspan="2"><a href="/dirlist.php?dir=subtitles%2Fjapanese%2FMushoku+Tensei%3A+Isekai+Ittara+Honki+Dasu%2F" class=""><strong>Mushoku Tensei: Isekai Ittara Honki Dasu</strong> </a></td> <td class="tdright" title="Dec 03 2023 05:13:17 AM" > 4&nbsp;months </td></tr>
# <tr><td colspan="2"><a href="/dirlist.php?dir=subtitles%2Fjapanese%2FSousou+no+Frieren%2F" class=""><strong>Sousou no Frieren</strong> </a></td> <td class="tdright" title="Apr 14 2024 06:23:19 PM" > 1&nbsp;week </td></tr>
RE_SUBTITLE_DIR = re.compile(
    r'<a href="/?(?P<abs_path>dirlist.php\?dir=[^"\']+)"[^<>]*>\s*<strong>\s*(?P<show_name>.+?)\s*</strong>\s*</a>.*<td class="tdright" title="(?P<mod_timestamp>[^<>"]+)"\s*>',
    flags=RE_FLAGS,
)

# <tr><td><a href="subtitles/japanese/Henjin no Salad Bowl/Henjin no Salad Bowl - 01 「麒麟がくる(異世界から)」 (TBS 1920x1080 x264 AAC).srt" class=""><strong>Henjin no Salad Bowl - 01 「麒麟がくる(異世界から)」 (TBS 1920x1080 x264 AAC).srt</strong> </a></td> <td class="tdleft"  title="29823"  > 29&nbsp;KB </td> <td class="tdright" title="Apr 05 2024 05:45:25 AM" > 3&nbsp;weeks </td></tr>
# <tr><td><a href="subtitles/japanese/Henjin no Salad Bowl/Henjin no Salad Bowl - 02 「ホームレス女騎士／はじめてのおしごと他」 (TBS 1920x1080 x264 AAC).srt" class=""><strong>Henjin no Salad Bowl - 02 「ホームレス女騎士／はじめてのおしごと他」 (TBS 1920x1080 x264 AAC).srt</strong> </a></td> <td class="tdleft"  title="31494"  > 31&nbsp;KB </td> <td class="tdright" title="Apr 12 2024 01:28:54 PM" > 2&nbsp;weeks </td></tr>
RE_SUBTITLE_FILE = re.compile(
    r'<a href="/?(?P<abs_path>subtitles/[^"\']+\.(?:zip|rar|7z|ass|srt|ssa))"[^<>]*>.*<td class="tdright" title="(?P<mod_timestamp>[^<>"]+)"\s*>',
    flags=RE_FLAGS,
)


def sanitize_name(title: str) -> str:
    return fs_name_strip(urllib.parse.unquote(title))


def find_all_subtitle_dirs(html_text: str) -> typing.Iterable[AnimeDir]:
    for match in re.finditer(RE_SUBTITLE_DIR, html_text):
        yield AnimeDir(
            url=f"{KITSUNEKKO_DOMAIN_URL}/{match.group('abs_path')}",
            show_name=sanitize_name(match.group("show_name")),
            # timestamp input looks like "Jul 15 2012 09:24:15 PM"
            mod_timestamp=datetime_from_str(match.group("mod_timestamp").strip()),
        )


def find_all_subtitle_files(html_text: str) -> typing.Iterable[SubtitleFile]:
    for match in re.finditer(RE_SUBTITLE_FILE, html_text):
        show_name, file_name = match.group("abs_path").split("/")[-2:]
        yield SubtitleFile(
            url=f"{KITSUNEKKO_DOMAIN_URL}/{urllib.parse.quote(match.group('abs_path'))}",
            show_name=sanitize_name(show_name),
            file_name=sanitize_name(file_name),
            # timestamp input looks like "Jul 15 2012 09:24:15 PM"
            mod_timestamp=datetime_from_str(match.group("mod_timestamp").strip()),
        )


def main():
    from pprint import pprint

    data_dir = pathlib.Path(__file__).parent.joinpath("../tests/data")

    html_text = data_dir.joinpath("main_dir_page.html").read_text()
    for anime_dir in itertools.islice(find_all_subtitle_dirs(html_text), 10):
        pprint(anime_dir, indent=2)

    html_text = data_dir.joinpath("subs_page.html").read_text()
    for sub_file in itertools.islice(find_all_subtitle_files(html_text), 10):
        pprint(sub_file, indent=2)


if __name__ == "__main__":
    main()
