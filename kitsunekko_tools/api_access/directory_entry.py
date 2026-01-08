# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import pathlib

from kitsunekko_tools.api_access.root_directory import (
    ApiDirectoryEntry,
    get_meta_file_path,
)
from kitsunekko_tools.common import datetime_now_utc, max_datetime
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.local_state import KitsuDirectoryMeta


def read_meta_file(meta_file_path: pathlib.Path) -> KitsuDirectoryMeta | None:
    try:
        with open(meta_file_path, encoding="utf-8") as f:
            assert meta_file_path.parent.is_dir(), "parent directory must exist."
            return KitsuDirectoryMeta.from_local_file(f, dir_path=meta_file_path.parent)
    except FileNotFoundError:
        return None


def keep_removed_values(remote_dir: ApiDirectoryEntry, local_state: KitsuDirectoryMeta | None) -> ApiDirectoryEntry:
    if not local_state:
        return remote_dir
    return dataclasses.replace(
        remote_dir,
        english_name=(remote_dir.english_name or local_state.english_name),
        japanese_name=(remote_dir.japanese_name or local_state.japanese_name),
        anilist_id=(remote_dir.anilist_id or local_state.anilist_id),
        tmdb_id=(remote_dir.tmdb_id or local_state.tmdb_id),
        last_modified=max_datetime(remote_dir.last_modified, local_state.last_modified),
    )


@dataclasses.dataclass(frozen=True)
class KitsuDirectoryEntry:
    remote_dir: ApiDirectoryEntry
    meta_file_path: pathlib.Path
    dir_listing_url: str
    local_state: KitsuDirectoryMeta | None

    @property
    def dir_path(self) -> pathlib.Path:
        return self.meta_file_path.parent

    @property
    def name(self) -> str:
        return self.remote_dir.name

    @classmethod
    def from_remote(cls, remote_dir: ApiDirectoryEntry, config: KitsuConfig):
        meta_file_path = get_meta_file_path(remote_dir, config)

        return cls(
            remote_dir=remote_dir,
            meta_file_path=meta_file_path,
            dir_listing_url=f"{config.api_url}/api/entries/{remote_dir.entry_id}/files",
            local_state=read_meta_file(meta_file_path),
        )

    def should_visit_directory(self) -> bool:
        """
        Visit the directory if the remote is more recent.
        """
        if not self.local_state:
            return True
        return self.remote_dir.last_modified > self.local_state.last_modified

    def write_meta(self) -> None:
        with open(self.meta_file_path, "w", encoding="utf-8") as of:
            keep_removed_values(self.remote_dir, self.local_state).write_to_file(of)

    def ensure_exists(self) -> None:
        self.meta_file_path.parent.mkdir(exist_ok=True)
