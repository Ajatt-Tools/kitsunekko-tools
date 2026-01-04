# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import csv
import io
import pathlib
import typing
from collections.abc import Iterable

from beartype import beartype

from kitsunekko_tools.common import SKIP_FILES, KitsuError
from kitsunekko_tools.config import KitsuConfig


@beartype
def get_tsv_reader(f: io.TextIOWrapper, fieldnames: typing.Sequence[str] | None = None) -> csv.DictReader:
    return csv.DictReader(
        f,
        fieldnames=fieldnames,
        dialect="excel-tab",
        delimiter="\t",
        quoting=csv.QUOTE_NONE,
    )


@beartype
def get_tsv_writer(of: io.TextIOWrapper, fieldnames: typing.Sequence[str]) -> csv.DictWriter:
    return csv.DictWriter(
        of,
        fieldnames=fieldnames,
        dialect="excel-tab",
        delimiter="\t",
        lineterminator="\n",
        quoting=csv.QUOTE_NONE,
    )


def iter_subtitle_directories(config: KitsuConfig) -> Iterable[pathlib.Path]:
    for entry in config.destination.resolve().iterdir():
        if not entry.is_dir():
            continue
        if entry.name in SKIP_FILES:
            continue
        yield entry


def iter_subtitle_files(directory: pathlib.Path) -> Iterable[pathlib.Path]:
    if not directory.is_dir():
        raise KitsuError(f"not a directory: {directory}")
    for path in directory.resolve().rglob("*"):
        if path.is_file() and path.name not in SKIP_FILES:
            yield path
