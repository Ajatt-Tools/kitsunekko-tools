# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import csv
import functools
import io
import pathlib
import shutil
import typing
import zipfile
from collections.abc import Iterable

from beartype import beartype

from kitsunekko_tools.common import SKIP_FILES, KitsuError, fs_name_strip
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import ARCHIVE_FILE_TYPES, SUBTITLE_FILE_TYPES


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
    for destination in config.all_destinations():
        for entry in destination.resolve().iterdir():
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


ARCHIVE_FILE_EXTENSIONS = frozenset(f".{ext}".lower() for ext in ARCHIVE_FILE_TYPES)
SUBTITLE_FILE_EXTENSIONS = frozenset(f".{ext}".lower() for ext in SUBTITLE_FILE_TYPES)


def iter_archive_files(dir_path: pathlib.Path) -> Iterable[pathlib.Path]:
    for item in dir_path.rglob("*"):
        if item.is_file() and item.suffix.lower() in ARCHIVE_FILE_EXTENSIONS:
            yield item


def is_macos_garbage(path_inside: pathlib.Path) -> bool:
    for parent in path_inside.parents:
        if parent.name == "__MACOSX":
            return True
    return False


def extract_from_zip(archive_path: pathlib.Path) -> None:
    """
    https://stackoverflow.com/questions/4917284/extract-files-from-zip-without-keeping-the-structure-using-python-zipfile/4917469#4917469
    """
    out_dir_path = archive_path.with_name(fs_name_strip(archive_path.stem))
    with zipfile.ZipFile(archive_path, "r") as za:
        for info in za.infolist():
            path_inside = pathlib.Path(info.filename)
            should_extract_file = (
                not is_macos_garbage(path_inside)
                and not info.is_dir()
                and path_inside.suffix in SUBTITLE_FILE_EXTENSIONS
            )
            if not should_extract_file:
                continue

            out_file_path = out_dir_path / fs_name_strip(path_inside.name)
            out_file_path.parent.mkdir(exist_ok=True, parents=True)
            with za.open(info) as src, open(out_file_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            print(f"extracted: {info.filename}")


def extract_archives(config: KitsuConfig) -> None:
    for archive in iter_archive_files(config.destination):
        print(f"found archive: {archive}")
        match archive.suffix:
            case ".zip":
                extract_from_zip(archive)
            case _:
                # TODO handle 7z and rar
                print(f"unsupported file type: {archive.suffix}")
