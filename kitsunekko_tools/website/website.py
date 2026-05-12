# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import concurrent.futures
import dataclasses
import datetime
import multiprocessing
import pathlib
import shutil
import typing
from collections.abc import Iterable
from typing import Self

from kitsunekko_tools.common import datetime_now_utc, epoch_datetime
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import (
    BUNDLED_RESOURCES_DIR,
    BUNDLED_TEMPLATES_DIR,
    TRASH_DIR_NAME,
)
from kitsunekko_tools.entry import EntryType
from kitsunekko_tools.filesystem import iter_subtitle_directories, iter_subtitle_files
from kitsunekko_tools.ignore import (
    FileMetaData,
    IgnoreTSVForDir,
    get_ignore_file_path_on_disk,
)
from kitsunekko_tools.local_state import KitsuDirectoryMeta, read_directory_meta
from kitsunekko_tools.website.context import (
    ENTRY_TEMPLATE_NAME,
    INDEX_TEMPLATE_NAME,
    NOT_FOUND_TEMPLATE_NAME,
    RESOURCES_DIR_NAME,
    ROBOTS_TEMPLATE_NAME,
    SITEMAP_TEMPLATE_NAME,
    WebSiteBuilderPaths,
    mk_context,
)
from kitsunekko_tools.website.templates import (
    JinjaEnvHolder,
    as_subtitle_download_url,
    render_template,
)

MAX_WORKERS = max(1, multiprocessing.cpu_count() - 1)


def collect_files(directory: pathlib.Path) -> Iterable[FileMetaData]:
    ignore_list = IgnoreTSVForDir(get_ignore_file_path_on_disk(directory))
    for file_path in iter_subtitle_files(directory):
        if not ignore_list.is_matching(file_path):
            ignore_list.add_file(file_path)
        yield ignore_list.file_info(file_path)
    ignore_list.commit()


@dataclasses.dataclass(frozen=True)
class LocalDirectoryEntry:
    meta: KitsuDirectoryMeta | None
    path_to_dir: pathlib.Path
    files_in_dir: list[FileMetaData]
    site_path_to_html_file: pathlib.Path
    is_drama: bool

    def filter_files(self, name_suffix: str) -> list[FileMetaData]:
        return [file for file in self.files_in_dir if file.path.name.endswith(name_suffix)]


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


def entry_sort_key(entry: LocalDirectoryEntry) -> tuple[float, str]:
    """Sort directory entries for the website index page, newest first.

    Used by WebSiteBuilder to order all entries on the index pages.

    Sorting order (ascending, so negated timestamps come first):
    1. Newest modification date first (negated timestamp). Entries without
       metadata fall back to the Unix epoch, pushing them to the end.
    2. Directory name as an alphabetical tiebreaker.
    """
    if entry.meta:
        return -entry.meta.last_modified.timestamp(), entry.meta.name
    return -epoch_datetime().timestamp(), entry.path_to_dir.name


def mk_shell_compatible_url_list(files: list[FileMetaData], cfg: KitsuConfig) -> str:
    return " ".join(f"'{link}'" for link in [as_subtitle_download_url(file.path, cfg) for file in files])


WGET_COMMAND_PREFIX = "wget --no-glob --no-clobber --content-disposition --trust-server-names --iri"


@dataclasses.dataclass(frozen=True)
class FileExtGroup:
    type: str
    files: list[FileMetaData]
    wget_command: str

    @classmethod
    def new(cls, group_type: str, files: list[FileMetaData], cfg: KitsuConfig) -> Self:
        return cls(
            group_type,
            files,
            wget_command=f"{WGET_COMMAND_PREFIX} {mk_shell_compatible_url_list(files, cfg)}",
        )


def mk_file_ext_groups(entry: LocalDirectoryEntry, cfg: KitsuConfig) -> list[FileExtGroup]:
    return [
        FileExtGroup.new("srt", entry.filter_files(".srt"), cfg),
        FileExtGroup.new("ass", entry.filter_files(".ass"), cfg),
        FileExtGroup.new("all", entry.files_in_dir, cfg),
    ]


def catalog_file_sort_key(file: FileMetaData) -> tuple[int, float, str, int]:
    """Sort subtitle files within a directory entry on the website.

    Used by the website builder to order subtitle files shown on each entry page.

    Trashed files (inside the trash subdirectory) get priority 1, others get 0,
    so trashed files always appear at the end of the file list.

    Negated timestamp: Newest modification date first.
    """
    if file.path.parent.name == TRASH_DIR_NAME:
        # place trashed files at the end of a file list.
        return 1, -file.last_modified.timestamp(), file.name, file.st_size
    return 0, -file.last_modified.timestamp(), file.name, file.st_size


class SiteMapPage(typing.NamedTuple):
    file_path: pathlib.Path
    last_modified: datetime.datetime


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
        for destination in self._paths.site_destinations.values():
            destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            self._paths.resources_dir_path,
            self._paths.site_dir_path / RESOURCES_DIR_NAME,
            dirs_exist_ok=True,
        )
        entries = sorted(self._walk_dirs(), key=entry_sort_key)
        self.generate_index_page(self._paths.index_file_path, [entry for entry in entries if not entry.is_drama])
        self.generate_index_page(self._paths.drama_index_file_path, [entry for entry in entries if entry.is_drama])
        self.generate_entry_pages(entries)
        self.generate_not_found_page()
        self.generate_sitemap(entries)
        self.generate_robots_txt()

    def generate_index_page(
        self,
        index_file_path: pathlib.Path,
        entries: list[LocalDirectoryEntry],
    ) -> None:
        """Generate the index page with all entries."""
        print(f"Rebuilding the index: {index_file_path.name}")
        context = mk_context(self._cfg, self._paths, index_file_path)
        context.ctx.entries = entries
        index_file_path.write_text(
            render_template(INDEX_TEMPLATE_NAME, context=context, template_env=self._tmpl_holder.template_env),
            encoding="utf-8",
        )

    def generate_not_found_page(self) -> None:
        """Generate the index page with all entries."""
        print(f"Rebuilding: {self._paths.not_found_file_path.name}")
        self._paths.not_found_file_path.write_text(
            render_template(
                NOT_FOUND_TEMPLATE_NAME,
                context=mk_context(self._cfg, self._paths, self._paths.not_found_file_path),
                template_env=self._tmpl_holder.template_env,
            ),
            encoding="utf-8",
        )

    def generate_robots_txt(self) -> None:
        """Generate robots.txt allowing all crawlers and pointing to sitemap."""
        print(f"Rebuilding: {self._paths.robots_file_path.name}")
        self._paths.robots_file_path.write_text(
            render_template(
                ROBOTS_TEMPLATE_NAME,
                context=mk_context(self._cfg, self._paths, self._paths.robots_file_path),
                template_env=self._tmpl_holder.template_env,
            ),
            encoding="utf-8",
        )

    def generate_sitemap(self, entries: list[LocalDirectoryEntry]) -> None:
        """Generate sitemap.xml with all index and entry page URLs."""
        print(f"Rebuilding: {self._paths.sitemap_file_path.name}")
        build_date = datetime_now_utc()
        sitemap_urls: list[SiteMapPage] = []

        for page_path in (self._paths.index_file_path, self._paths.drama_index_file_path):
            sitemap_urls.append(
                SiteMapPage(
                    file_path=page_path,
                    last_modified=build_date,
                )
            )

        for entry in entries:
            sitemap_urls.append(
                SiteMapPage(
                    file_path=entry.site_path_to_html_file,
                    last_modified=entry.meta.last_modified if entry.meta else build_date,
                )
            )

        context = mk_context(self._cfg, self._paths, self._paths.sitemap_file_path)
        context.ctx.sitemap_urls = sitemap_urls
        self._paths.sitemap_file_path.write_text(
            render_template(SITEMAP_TEMPLATE_NAME, context=context, template_env=self._tmpl_holder.template_env),
            encoding="utf-8",
        )

    def _walk_dirs(self) -> Iterable[LocalDirectoryEntry]:
        print("Collecting entries...")
        for dir_path in iter_subtitle_directories(self._cfg):
            try:
                meta = read_directory_meta(dir_path)
            except FileNotFoundError:
                meta = None
            is_drama = bool(meta and meta.is_drama())
            entry_type = meta.entry_type if meta else EntryType.unsorted
            yield LocalDirectoryEntry(
                meta=meta,
                path_to_dir=dir_path,
                files_in_dir=sorted(collect_files(dir_path), key=catalog_file_sort_key),
                site_path_to_html_file=self._mk_path_to_entry_html_file(dir_path.name, entry_type),
                is_drama=is_drama,
            )

    def generate_entry_pages(self, entries: list[LocalDirectoryEntry]) -> None:
        """
        Generate each entry page.
        """
        print("Rebuilding the entries...")
        # We can use a with statement to ensure threads are cleaned up promptly
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for entry in entries:
                executor.submit(self.generate_entry_page, entry=entry)

    def generate_entry_page(self, entry: LocalDirectoryEntry) -> None:
        """
        Generate entry page.
        """
        context = mk_context(self._cfg, self._paths, entry.site_path_to_html_file)
        context.ctx.entry = entry
        context.ctx.file_ext_groups = mk_file_ext_groups(entry, self._cfg)
        if entry.meta:
            context.ctx.entry_name = entry.meta.name
            context.ctx.search_link = make_search_link(is_anime=entry.meta.is_anime(), query=entry.meta.name)
        else:
            context.ctx.entry_name = entry.path_to_dir.name
            context.ctx.search_link = make_search_link(is_anime=True, query=context.ctx.entry_name)

        html_content = render_template(ENTRY_TEMPLATE_NAME, context, self._tmpl_holder.template_env)
        entry.site_path_to_html_file.write_text(html_content, encoding="utf-8")

    def copy_site_resources(self) -> None:
        print("Removing old resources and templates.")
        shutil.rmtree(self._paths.resources_dir_path, ignore_errors=True)
        shutil.rmtree(self._paths.templates_dir_path, ignore_errors=True)
        print("Copying resources.")
        shutil.copytree(BUNDLED_RESOURCES_DIR, self._paths.resources_dir_path)
        print("Copying templates.")
        shutil.copytree(BUNDLED_TEMPLATES_DIR, self._paths.templates_dir_path)

    def _mk_path_to_entry_html_file(self, entry_name: str, entry_type: EntryType) -> pathlib.Path:
        return self._paths.site_destinations[entry_type] / f"{name_to_addr(entry_name)}.html"


def build_website(config: KitsuConfig) -> None:
    b = WebSiteBuilder(config)
    b.build()
