# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import datetime
import pathlib
from types import SimpleNamespace

from kitsunekko_tools.common import datetime_now_utc
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.entry import EntryType
from kitsunekko_tools.website.filesystem import full_site_url_to_resource

INDEX_TEMPLATE_NAME = "index.html"
NOT_FOUND_TEMPLATE_NAME = "not_found.html"
DRAMA_INDEX_TEMPLATE_NAME = "drama.html"
ENTRY_TEMPLATE_NAME = "entry.html"
SITE_BUILD_LOCATION_NAME = "_site"
TEMPLATES_DIR_NAME = "templates"
RESOURCES_DIR_NAME = "resources"
CSS_FILE_NAME = "site.css"
JS_FILE_NAME = "site.js"
FAVICON_FILE_NAME = "logo.webp"


@dataclasses.dataclass(frozen=True)
class WebSiteBuilderPaths:
    work_root: pathlib.Path
    site_dir_path: pathlib.Path
    templates_dir_path: pathlib.Path
    resources_dir_path: pathlib.Path
    index_file_path: pathlib.Path
    not_found_file_path: pathlib.Path
    drama_index_file_path: pathlib.Path
    site_destinations: dict[EntryType, pathlib.Path]

    @classmethod
    def new(cls, config: KitsuConfig):
        work_root = config.destination.resolve().parent
        site_dir_path = work_root.joinpath(SITE_BUILD_LOCATION_NAME)
        return cls(
            work_root=work_root,
            site_dir_path=site_dir_path,
            templates_dir_path=work_root.joinpath(TEMPLATES_DIR_NAME),
            resources_dir_path=work_root.joinpath(RESOURCES_DIR_NAME),
            index_file_path=site_dir_path / INDEX_TEMPLATE_NAME,
            not_found_file_path=site_dir_path / NOT_FOUND_TEMPLATE_NAME,
            drama_index_file_path=site_dir_path / DRAMA_INDEX_TEMPLATE_NAME,
            site_destinations={entry_type: site_dir_path.joinpath(entry_type.name) for entry_type in EntryType},
        )


@dataclasses.dataclass(frozen=True)
class SiteContext:
    cfg: KitsuConfig
    ctx: SimpleNamespace
    paths: WebSiteBuilderPaths


def mk_context(config: KitsuConfig, paths: WebSiteBuilderPaths, output_file_path: pathlib.Path) -> SiteContext:
    # Get current time for build date
    now = datetime_now_utc()

    return SiteContext(
        cfg=config,
        paths=paths,
        ctx=SimpleNamespace(
            # Paths
            output_file_path=output_file_path,
            site_dir_path=paths.site_dir_path,
            css_file_path=paths.site_dir_path / RESOURCES_DIR_NAME / CSS_FILE_NAME,
            js_file_path=paths.site_dir_path / RESOURCES_DIR_NAME / JS_FILE_NAME,
            favicon_path=paths.site_dir_path / RESOURCES_DIR_NAME / FAVICON_FILE_NAME,
            # Return the URL by joining the global URL with the relative path
            request_url=full_site_url_to_resource(config.site_url, paths.site_dir_path, output_file_path),
            site_blog_url=config.site_blog_url.rstrip("/"),
            site_description="Japanese subtitles for Japanese anime, dramas, TV shows, and movies",
            site_title="Japanese subtitles - AJATT",
            site_author="Tatsumoto Ren",
            site_keywords="japanese, subtitles, anime, TV, dramas, AJATT",
            # Dates
            current_year=now.year,
            date_now=now,
            # Entry types
            EntryType=EntryType,
        ),
    )
