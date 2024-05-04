# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import datetime
import functools
import io
import os
import os.path
import pathlib
import tomllib
import typing

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.consts import PROG_NAME, SETTINGS_FILE_NAME

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
def config_locations() -> typing.Sequence[pathlib.Path]:
    return (
        get_xdg_config_dir() / PROG_NAME / SETTINGS_FILE_NAME,
        pathlib.Path.home() / SETTINGS_FILE_NAME,
        pathlib.Path("/etc/") / PROG_NAME / SETTINGS_FILE_NAME,
    )


def default_config_not_found_description() -> str:
    with io.StringIO() as si:
        si.write("Couldn't find config file. ")
        si.write("Create the file in one of the following locations:\n")
        si.write("\n".join(f"・ {location}" for location in config_locations()))
        return si.getvalue()


@dataclasses.dataclass(frozen=True)
class ConfigFileNotFoundError(KitsuException, FileNotFoundError):
    what: str = default_config_not_found_description()


@dataclasses.dataclass(frozen=True)
class DestDirNotFoundError(KitsuException):
    what: str


@dataclasses.dataclass(frozen=True)
class ConfigFileInvalidError(KitsuException, ValueError):
    what: str


def as_toml_str(d: dict[str, str | int | dict]) -> str:
    with io.StringIO() as si:
        for key, value in d.items():
            match value:
                case None:
                    si.write(f'{key} = ""\n')
                case frozenset():
                    si.write(f"{key} = {list(value)}\n")
                case str() | pathlib.Path():
                    si.write(f'{key} = "{value}"\n')
                case int():
                    si.write(f"{key} = {value}\n")
                case datetime.timedelta():
                    value = str(value).split(",")[0]
                    si.write(f'{key} = "{value}"\n')
                case dict():
                    si.write(f"[{key}]\n")
                    si.write(as_toml_str(value))
                case _:
                    raise RuntimeError(f"Unknown value type {type(value)}")
        return si.getvalue()


class ApiHeaders(typing.TypedDict):
    Authorization: str


def convert_time_delta(skip_older: str | datetime.timedelta) -> datetime.timedelta:
    if isinstance(skip_older, datetime.timedelta):
        return skip_older
    assert isinstance(skip_older, str), "Parameter 'skip_older' is expected to be a string."
    period, time_unit = skip_older.split()
    return datetime.timedelta(**{time_unit: int(period)})


@dataclasses.dataclass(frozen=True)
class KitsuConfig:
    destination: pathlib.Path = pathlib.Path.home() / "kitsunekko"
    proxy: str | None = "socks5://127.0.0.1:9050"
    download_root: str = "https://kitsunekko.net/dirlist.php?dir=subtitles/japanese/"  # scrap target
    timeout: int = 120
    skip_older: datetime.timedelta = datetime.timedelta(days=30)  # 30 days
    api_url: str = "https://kitsunekko.net"  # URL of a subtitle server. Normally looks like 'https://example.com'.
    api_key: str = ""  # API key of the subtitle server
    allowed_file_types: frozenset[str] = dataclasses.field(
        default_factory=lambda: frozenset(["ssa", "ass", "srt", "zip", "rar", "7z"])
    )
    headers: dict[str, str] = dataclasses.field(default_factory=lambda: DEFAULT_HEADERS.copy())

    @classmethod
    def from_file(cls, file: typing.BinaryIO) -> typing.Self:
        instance = cls(**tomllib.load(file))
        if "dirlist.php?dir=" not in instance.download_root:
            raise ConfigFileInvalidError("Download root doesn't appear to be a valid kitsunekko URL.")
        return dataclasses.replace(
            instance,
            destination=pathlib.Path(instance.destination).expanduser(),
            skip_older=convert_time_delta(instance.skip_older),
            proxy=instance.proxy or None,  # coerce proxy to null if it's empty
            allowed_file_types=frozenset(instance.allowed_file_types),
            api_key=os.getenv("KITSU_API_KEY", instance.api_key),
            api_url=os.getenv("KITSU_API_URL", instance.api_url),
        )

    def raise_for_destination(self) -> None:
        if not self.destination.is_dir():
            raise DestDirNotFoundError(f"Destination directory does not exist: {self.destination}")

    def as_toml_str(self) -> str:
        return as_toml_str(dataclasses.asdict(self))

    def api_headers(self) -> ApiHeaders:
        return {"Authorization": self.api_key}

    def is_allowed_file_type(self, file_path: pathlib.Path) -> bool:
        return any(file_path.name.endswith(f".{ext}") for ext in self.allowed_file_types)


class ReadConfigResult(typing.NamedTuple):
    data: KitsuConfig
    file_path: pathlib.Path


@functools.cache
def read_config_file(config_file_path: pathlib.Path) -> ReadConfigResult:
    try:
        with open(config_file_path, "rb") as f:
            return ReadConfigResult(KitsuConfig.from_file(f), pathlib.Path(config_file_path))
    except FileNotFoundError as ex:
        raise ConfigFileNotFoundError() from ex


@functools.cache
def get_config(config_file_path: pathlib.Path | str | None = None) -> ReadConfigResult:
    if config_file_path:
        return read_config_file(pathlib.Path(config_file_path).expanduser())
    for config_file_path in config_locations():
        try:
            return read_config_file(config_file_path)
        except ConfigFileNotFoundError:
            continue
    raise ConfigFileNotFoundError()


class Config:
    """
    Proxy to get access to the config.
    """

    def __init__(self, config_path: str | None):
        self._config_path = config_path

    def load(self) -> ReadConfigResult:
        return get_config(self._config_path)

    def data(self) -> KitsuConfig:
        return self.load().data

    def file_path(self) -> pathlib.Path:
        return self.load().file_path

    def default_file_path(self) -> pathlib.Path:
        return pathlib.Path(self._config_path or config_locations()[0])

    def create_config_file(self) -> pathlib.Path:
        config_file_path = self.default_file_path()
        if config_file_path.is_file():
            raise RuntimeError(f"File already exists: {config_file_path}")
        config_file_path.parent.mkdir(exist_ok=True, parents=True)
        config_file_path.write_text(KitsuConfig().as_toml_str(), encoding="utf-8")
        return config_file_path


def main():
    from pprint import pprint

    pprint(KitsuConfig(), indent=2)


if __name__ == "__main__":
    main()
