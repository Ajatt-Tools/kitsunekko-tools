# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import pathlib
import shutil
from collections.abc import Iterable

from kitsunekko_tools.api_access.root_directory import KitsuDirectoryMeta
from kitsunekko_tools.common import SKIP_FILES
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import BUNDLED_RESOURCES_DIR, BUNDLED_TEMPLATES_DIR
from kitsunekko_tools.sanitize import iter_subtitle_directories, read_directory_meta
from kitsunekko_tools.website.context import (
    ENTRY_TEMPLATE_NAME,
    INDEX_TEMPLATE_NAME,
    RESOURCES_DIR_NAME,
    WebSiteBuilderPaths,
    mk_context,
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
    is_drama: bool


def name_to_addr(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


@dataclasses.dataclass(frozen=True)
class EntryExternalSearchLink:
    url: str
    text: str


def make_search_link(is_anime: bool, query: str) -> EntryExternalSearchLink:
    if is_anime:
        return EntryExternalSearchLink(url=f"https://myanimelist.net/anime.php?q={query}", text="Search MAL")
    else:
        return EntryExternalSearchLink(url=f"https://mydramalist.com/search?q={query}", text="Search MDL")


class WebSiteBuilder:
    _cfg: KitsuConfig

    def __init__(self, config: KitsuConfig) -> None:
        self._cfg = config
        self._cfg.raise_for_destination()
        self._paths = WebSiteBuilderPaths.new(config)
        self._tmpl_holder = JinjaEnvHolder(
            self._cfg,
            templates_dir_path=self._paths.templates_dir_path,
            site_dir_path=self._paths.site_dir_path,
        )

    def build(self) -> None:
        self._paths.site_dir_path.mkdir(parents=True, exist_ok=True)
        self._paths.anime_entries_dir_path.mkdir(parents=True, exist_ok=True)
        self._paths.drama_entries_dir_path.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            self._paths.resources_dir_path,
            self._paths.site_dir_path / RESOURCES_DIR_NAME,
            dirs_exist_ok=True,
        )
        entries = sorted(self._walk_dirs(), key=lambda entry: entry.path_to_dir)
        self.generate_index_page(self._paths.index_file_path, [entry for entry in entries if not entry.is_drama])
        self.generate_index_page(self._paths.drama_index_file_path, [entry for entry in entries if entry.is_drama])
        self.generate_entry_pages(entries)

    def generate_index_page(
        self,
        index_file_path: pathlib.Path,
        entries: list[LocalDirectoryEntry],
    ) -> None:
        """Generate the index page with all entries."""
        print(f"Rebuilding the index: {index_file_path.name}")
        context = mk_context(self._cfg, self._paths, index_file_path)
        context.ctx.entries = entries
        html_content = render_template(INDEX_TEMPLATE_NAME, context, self._tmpl_holder.template_env)
        index_file_path.write_text(html_content, encoding="utf-8")

    def _walk_dirs(self) -> Iterable[LocalDirectoryEntry]:
        print("Collecting entries", end="")
        for dir_path in iter_subtitle_directories(self._cfg):
            print(".", end="")
            try:
                meta = read_directory_meta(dir_path)
            except FileNotFoundError:
                meta = None
            is_drama = bool(meta and meta.is_drama())
            yield LocalDirectoryEntry(
                meta=meta,
                path_to_dir=dir_path,
                files_in_dir=collect_files(dir_path),
                site_path_to_html_file=self._mk_path_to_entry_html_file(is_drama, dir_path),
                is_drama=is_drama,
            )
        print("")

    def generate_entry_pages(self, entries: list[LocalDirectoryEntry]) -> None:
        """Generate the index page with all entries."""
        print("Rebuilding the entries", end="")
        for entry in entries:
            print(".", end="")
            context = mk_context(self._cfg, self._paths, entry.site_path_to_html_file)
            context.ctx.entry = entry
            if entry.meta:
                context.ctx.entry_name = entry.meta.name
                context.ctx.search_link = make_search_link(is_anime=entry.meta.is_anime(), query=entry.meta.name)
            else:
                context.ctx.entry_name = entry.path_to_dir.name
                context.ctx.search_link = make_search_link(is_anime=True, query=context.ctx.entry_name)

            html_content = render_template(ENTRY_TEMPLATE_NAME, context, self._tmpl_holder.template_env)
            entry.site_path_to_html_file.write_text(html_content, encoding="utf-8")
        print("")

    def copy_site_resources(self) -> None:
        print("Removing old resources and templates.")
        shutil.rmtree(self._paths.resources_dir_path, ignore_errors=True)
        shutil.rmtree(self._paths.templates_dir_path, ignore_errors=True)
        print("Copying resources.")
        shutil.copytree(BUNDLED_RESOURCES_DIR, self._paths.resources_dir_path)
        print("Copying templates.")
        shutil.copytree(BUNDLED_TEMPLATES_DIR, self._paths.templates_dir_path)

    def _mk_path_to_entry_html_file(self, is_drama: bool, dir_path: pathlib.Path) -> pathlib.Path:
        file_name = f"{name_to_addr(dir_path.name)}.html"
        if is_drama:
            return self._paths.drama_entries_dir_path / file_name
        return self._paths.anime_entries_dir_path / file_name


def build_website(config: KitsuConfig) -> None:
    b = WebSiteBuilder(config)
    b.build()
