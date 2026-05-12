# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import pathlib

from kitsunekko_tools.api_access.root_directory import KitsunekkoId, parse_api_time
from kitsunekko_tools.entry import EntryType
from kitsunekko_tools.ignore import FileMetaData, IgnoreFileEntry
from kitsunekko_tools.local_state import KitsuDirectoryMeta
from kitsunekko_tools.scrapper.types import NoMetaDirectoryEntry
from kitsunekko_tools.website.website import LocalDirectoryEntry


def year(year_: int) -> datetime.datetime:
    """Create a UTC datetime for January 1st of the given year."""
    return datetime.datetime(year=year_, month=1, day=1, tzinfo=datetime.UTC)


def mk_kitsu_meta(*, name: str, year_: int = 2024) -> KitsuDirectoryMeta:
    """Create a KitsuDirectoryMeta for testing."""
    return KitsuDirectoryMeta(
        entry_id=KitsunekkoId(1),
        name=name,
        entry_type=EntryType.anime_tv,
        last_modified=year(year_),
        dir_path=pathlib.Path(f"/tmp/{name}"),
    )


def mk_no_meta(*, name: str, year_: int = 2024) -> NoMetaDirectoryEntry:
    """Create a NoMetaDirectoryEntry for testing."""
    return NoMetaDirectoryEntry(
        dir_path=pathlib.Path(f"/tmp/{name}"),
        name=name,
        last_modified=year(year_),
    )


def mk_ignore_entry(*, name: str, st_size: int = 100, year_: int = 2024) -> IgnoreFileEntry:
    """Create an IgnoreFileEntry for testing."""
    return IgnoreFileEntry(name=name, last_modified=year(year_), st_size=st_size)


def mk_real_ignore_entry(*, name: str, st_size: int, last_modified: str) -> IgnoreFileEntry:
    """Create an IgnoreFileEntry from real API data."""
    return IgnoreFileEntry(name=name, last_modified=parse_api_time(last_modified), st_size=st_size)


def mk_entry(*, name: str, year_: int = 2024, has_meta: bool = True) -> LocalDirectoryEntry:
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


def make_api_entry(
    *,
    entry_id: int = 1,
    name: str = "Test",
    entry_type: EntryType = EntryType.anime_tv,
    last_modified: datetime.datetime = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
) -> KitsuDirectoryMeta:
    """Create a KitsuDirectoryMeta for testing."""
    return KitsuDirectoryMeta(
        entry_id=KitsunekkoId(entry_id),
        name=name,
        entry_type=entry_type,
        last_modified=last_modified,
        dir_path=pathlib.Path(f"/tmp/{name}"),
    )


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
