# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import pathlib
import shutil
from typing import Iterable

from kitsunekko_tools.api_access.root_directory import KitsuDirectoryMeta
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.sanitize import SKIP_FILES, read_directory_meta
from kitsunekko_tools.website.context import (
    mk_context,
    INDEX_TEMPLATE_NAME,
    RESOURCES_DIR_NAME,
    CSS_FILE_NAME,
    TEMPLATES_DIR_NAME,
    SITE_BUILD_LOCATION_NAME,
    ENTRY_TEMPLATE_NAME,
)
from kitsunekko_tools.website.templates import JinjaEnvHolder, render_template


def collect_files(directory: pathlib.Path) -> list[pathlib.Path]:
    return [p.resolve() for p in directory.rglob("*") if p.is_file() and p.name not in SKIP_FILES]


@dataclasses.dataclass(frozen=True)
class LocalDirectoryEntry:
    meta: KitsuDirectoryMeta | None
    path_to_dir: pathlib.Path
    files_in_dir: list[pathlib.Path]
    site_path_to_html_file: pathlib.Path


def name_to_addr(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


class WebSiteBuilder:
    _cfg: KitsuConfig

    def __init__(self, config: KitsuConfig) -> None:
        self._cfg = config
        self._work_root = config.destination.resolve().parent
        self._site_dir_path = self._work_root.joinpath(SITE_BUILD_LOCATION_NAME)
        self._templates_dir_path = self._work_root.joinpath(TEMPLATES_DIR_NAME)
        self._resources_dir_path = self._work_root.joinpath(RESOURCES_DIR_NAME)
        self._tmpl_holder = JinjaEnvHolder(
            self._cfg, templates_dir_path=self._templates_dir_path, site_dir_path=self._site_dir_path
        )
        self._index_file_path = self._site_dir_path / INDEX_TEMPLATE_NAME
        self._entries_dir_path = self._index_file_path.parent / "entries"

    def build(self) -> None:
        self._site_dir_path.mkdir(parents=True, exist_ok=True)
        self._entries_dir_path.mkdir(parents=True, exist_ok=True)

        shutil.copytree(self._resources_dir_path, self._site_dir_path / RESOURCES_DIR_NAME, dirs_exist_ok=True)
        entries = list(self._walk_dirs())
        print("Rebuilding the index.")
        self.generate_index_page(entries)
        print("Rebuilding the entries", end="")
        for entry in entries:
            self.generate_entry_page(entry)
        print("")

    def generate_index_page(
        self,
        entries: list[LocalDirectoryEntry],
    ) -> None:
        """Generate the index page with all entries."""
        context = mk_context(self._cfg, self._site_dir_path, self._index_file_path)
        context.ctx.entries = entries
        html_content = render_template(INDEX_TEMPLATE_NAME, context, self._tmpl_holder.template_env)
        self._index_file_path.write_text(html_content, encoding="utf-8")

    def _walk_dirs(self) -> Iterable[LocalDirectoryEntry]:
        for dir_path in self._cfg.destination.resolve().iterdir():
            if dir_path.name in SKIP_FILES:
                continue
            try:
                meta = read_directory_meta(dir_path)
            except FileNotFoundError:
                meta = None
            yield LocalDirectoryEntry(
                meta=meta,
                path_to_dir=dir_path,
                files_in_dir=collect_files(dir_path),
                site_path_to_html_file=self._entries_dir_path / f"{name_to_addr(dir_path.name)}.html",
            )

    def generate_entry_page(self, entry: LocalDirectoryEntry) -> None:
        """Generate the index page with all entries."""
        print(".", end="")
        context = mk_context(self._cfg, self._site_dir_path, entry.site_path_to_html_file)
        context.ctx.entry = entry
        if entry.meta:
            context.ctx.entry_name = entry.meta.name
        else:
            context.ctx.entry_name = entry.path_to_dir.name

        html_content = render_template(ENTRY_TEMPLATE_NAME, context, self._tmpl_holder.template_env)
        entry.site_path_to_html_file.write_text(html_content, encoding="utf-8")


def build_website(config: KitsuConfig) -> None:
    b = WebSiteBuilder(config)
    b.build()
