# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import csv
import io
import typing

from beartype import beartype


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
