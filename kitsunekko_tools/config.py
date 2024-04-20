# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import fnmatch
import functools
import io
import os.path
import pathlib
import sys
import tomllib
import typing

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.consts import *

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:108.0) Gecko/20100101 Firefox/108.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
    "Accept-Encoding": "none",
    "Accept-Language": "en-US,en;q=0.8",
    "Connection": "keep-alive",
}


@functools.cache
def get_xdg_config_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config"))


@functools.cache
def config_locations():
    return (
        get_xdg_config_dir() / PROG_NAME / SETTINGS_FILE_NAME,
        pathlib.Path.home() / SETTINGS_FILE_NAME,
        pathlib.Path("/etc/") / PROG_NAME / SETTINGS_FILE_NAME,
    )


class ConfigFileNotFoundError(KitsuException, FileNotFoundError):
    @property
    def what(self) -> str:
        with io.StringIO() as si:
            si.write("Couldn't find config file. ")
            si.write("Create the file in one of the following locations:\n")
            si.write("\n".join(f"・ {location}" for location in config_locations()))
            return si.getvalue()


@dataclasses.dataclass
class KitsuConfig:
    destination: pathlib.Path = "/mnt/archive/japanese/kitsunekko-mirror"
    proxy: str = "socks5://127.0.0.1:9050"
    download_root: str = "https://kitsunekko.net/dirlist.php?dir=subtitles/japanese/"
    timeout: int = 120
    headers: dict[str, str] = dataclasses.field(default_factory=lambda: DEFAULT_HEADERS.copy())

    def __post_init__(self):
        self.destination = pathlib.Path(self.destination)

    def as_toml_str(self) -> str:
        with io.StringIO() as si:
            for key, value in dataclasses.asdict(self).items():
                match value:
                    case str():
                        si.write(f'{key} = "{value}"\n')
                    case int():
                        si.write(f"{key} = {value}\n")
                    case dict():
                        si.write(f"[{key}]\n")
                        si.write("\n".join(f'{k} = "{v}"' for k, v in value.items()))
                    case _:
                        raise RuntimeError(f"Unknown value type {type(value)}")
            return si.getvalue()

    @staticmethod
    def default_location() -> pathlib.Path:
        return config_locations()[0]


class ReadConfigResult(typing.NamedTuple):
    data: KitsuConfig
    file_path: pathlib.Path


@functools.cache
def get_config() -> ReadConfigResult:
    for config_file_path in config_locations():
        if os.path.isfile(config_file_path):
            print(f"Reading config file: {config_file_path}", file=sys.stderr)
            with open(config_file_path, "rb") as f:
                return ReadConfigResult(KitsuConfig(**tomllib.load(f)), config_file_path)
    raise ConfigFileNotFoundError()
