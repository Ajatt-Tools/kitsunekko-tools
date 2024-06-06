# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import datetime
import json
from collections.abc import Sequence

import pytest

from kitsunekko_tools.api_access.root_directory import (
    ApiDirectoryDict,
    ApiDirectoryEntry,
    iter_catalog_directories,
)
from tests.test_parser import DATA_DIR


@pytest.fixture(params=["entries_search_anime_response.json", "entries_search_dramas_response.json"])
def search_response_json(request) -> Sequence[ApiDirectoryDict]:
    with open(DATA_DIR.joinpath(request.param), encoding="utf-8") as f:
        return json.load(f)


def test_shows_in_root_dir(search_response_json: Sequence[ApiDirectoryDict]) -> None:
    dirs: list[ApiDirectoryEntry] = [*iter_catalog_directories(search_response_json)]
    assert len(dirs) > 0
    assert all(dir_.entry_id > 0 for dir_ in dirs)
    assert all(dir_.name for dir_ in dirs)
    date_threshold = datetime.datetime.fromisoformat("2012-07-15 20:21:54+00:00")
    assert all(dir_.last_modified > date_threshold for dir_ in dirs)
