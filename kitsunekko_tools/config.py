# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import fnmatch
import functools
import json
import os.path
import sys
import pathlib
from kitsunekko_tools.consts import *

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:108.0) Gecko/20100101 Firefox/108.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
    "Accept-Encoding": "none",
    "Accept-Language": "en-US,en;q=0.8",
    "Connection": "keep-alive",
}


@dataclasses.dataclass(frozen=True)
class KitsuConfigData:
    destination: str = "/mnt/archive/japanese/kitsunekko-mirror"
    proxy: str = "socks5://127.0.0.1:9050"
    download_root: str = "https://kitsunekko.net/dirlist.php?dir=subtitles/japanese/"
    timeout: int = 120
    headers: dict[str, str] = dataclasses.field(default_factory=lambda: DEFAULT_HEADERS.copy())


@functools.cache
def get_xdg_config_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config"))


@functools.cache
def config_locations():
    return (
        get_xdg_config_dir() / PROG_NAME / SETTINGS_FILE_NAME,
        get_xdg_config_dir() / SETTINGS_FILE_NAME,
        pathlib.Path("/etc/") / PROG_NAME / SETTINGS_FILE_NAME,
    )


def read_config():
    for config_file_path in config_locations():
        if os.path.isfile(config_file_path):
            print(f"Reading config file: {config_file_path}", file=sys.stderr)
            with open(config_file_path, encoding="utf8") as f:
                return KitsuConfigData(**json.load(f))
    raise RuntimeError("Couldn't find config file.")


class IgnoreList:
    def __init__(self):
        self._ignore_filepath = os.path.join(config.destination, IGNORE_FILENAME)
        self._patterns = set()
        if os.path.isfile(self._ignore_filepath):
            with open(self._ignore_filepath, encoding="utf8") as f:
                print(f"Reading ignore file: {self._ignore_filepath}", file=sys.stderr)
                self._patterns.update(filter(bool, map(str.strip, f.read().splitlines())))
        print("Ignore patterns:")
        print("\n".join(self._patterns))

    def is_matching(self, file_path: str) -> bool:
        path_dest_stripped = os.path.relpath(file_path, config.destination)
        return any(fnmatch.fnmatch(path_dest_stripped, pattern) for pattern in self._patterns)


config = read_config()
ignore = IgnoreList()
