import datetime
import re
from collections.abc import Iterable

from kitsunekko_tools.common import fs_name_strip
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.filesystem import iter_subtitle_directories
from kitsunekko_tools.local_state import KitsuDirectoryMeta, read_directory_meta
from kitsunekko_tools.scrapper.types import NoMetaDirectoryEntry

RE_INSIGNIFICANT_CHARS = re.compile(
    r"[\- ー,.。、！!@#$%^&*()_=+＠＃＄％＾△＆＊（）＋＝「」\s\\\n\t\r\[\]{}<>?/\'\":`|;〄〇〈〉〓〔〕〖〗〘〙〚〛〝〞〟〠〡〢〣〥〦〧〨〭〮〯〫〬〶〷〸〹〺〻〼〾〿？…ヽヾゞ〱〲〳〵〴［］｛｝｟｠゠‥•◦﹅﹆♪♫♬♩ⓍⓁⓎ仝　・※【】〒◎×〃゜『』《》～〜~〽☆∀∕]+",
    flags=re.MULTILINE | re.IGNORECASE,
)

type LocalDirectoryMeta = KitsuDirectoryMeta | NoMetaDirectoryEntry


def name_strip_insignificant_chars(name: str) -> str:
    return re.sub(RE_INSIGNIFICANT_CHARS, "", name).lower()


def iter_lookup_keys(meta: LocalDirectoryMeta) -> Iterable[str]:
    if meta.name:
        yield name_strip_insignificant_chars(meta.name)
        yield name_strip_insignificant_chars(fs_name_strip(meta.name))
    if meta.english_name:
        yield name_strip_insignificant_chars(meta.english_name)
        yield name_strip_insignificant_chars(fs_name_strip(meta.english_name))
    if meta.japanese_name:
        yield name_strip_insignificant_chars(meta.japanese_name)
        yield name_strip_insignificant_chars(fs_name_strip(meta.japanese_name))
    yield name_strip_insignificant_chars(meta.dir_path.name)
    yield name_strip_insignificant_chars(fs_name_strip(meta.dir_path.name))


def build_lookup_dicts(config: KitsuConfig) -> dict[str, list[LocalDirectoryMeta]]:
    print("building lookup dict to match orphans...")
    lookup_key_to_meta = {}
    for directory in iter_subtitle_directories(config):
        try:
            meta = read_directory_meta(directory)
        except FileNotFoundError:
            meta = NoMetaDirectoryEntry.from_dir(directory)
        for lookup_key in iter_lookup_keys(meta):
            lookup_key_to_meta.setdefault(lookup_key, list()).append(meta)
    return lookup_key_to_meta


def local_dir_sort_key(entry: LocalDirectoryMeta) -> tuple[int, datetime.datetime]:
    """
    Key used to sort entries based on modification date.
    """
    match entry:
        case KitsuDirectoryMeta():
            return 1, entry.last_modified
        case NoMetaDirectoryEntry():
            return 0, entry.last_modified
        case _:
            raise ValueError(f"unknown type: {type(entry)}")


class MatcherKeyError(KeyError):
    pass


class DirPathMatcher:
    _config: KitsuConfig
    _lookup_key_to_meta: dict[str, list[LocalDirectoryMeta]]

    def __init__(self, config: KitsuConfig) -> None:
        self._config = config
        self._lookup_key_to_meta = build_lookup_dicts(self._config)

    def find_best_matching_entry(self, directory_name: str) -> LocalDirectoryMeta:
        for try_key in (
            name_strip_insignificant_chars(fs_name_strip(directory_name)),
            name_strip_insignificant_chars(directory_name),
        ):
            try:
                # Get the most recently modified directory.
                # Directories without metadata have modification timestamp set to 0.
                return max(
                    self._lookup_key_to_meta[try_key],
                    key=local_dir_sort_key,
                )
            except KeyError:
                continue
        raise MatcherKeyError(f"can't find a match for {directory_name}")
