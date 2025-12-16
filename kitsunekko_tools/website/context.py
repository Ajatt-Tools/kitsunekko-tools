# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import datetime
import pathlib
from types import SimpleNamespace

from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.website.filesystem import full_site_url_to_resource

INDEX_TEMPLATE_NAME = "index.html"
ENTRY_TEMPLATE_NAME = "entry.html"
SITE_BUILD_LOCATION_NAME = "_site"
TEMPLATES_DIR_NAME = "templates"
RESOURCES_DIR_NAME = "resources"
CSS_FILE_NAME = "site.css"
FAVICON_FILE_NAME = "logo.webp"


@dataclasses.dataclass(frozen=True)
class SiteContext:
    cfg: KitsuConfig
    ctx: SimpleNamespace


def mk_context(config: KitsuConfig, site_dir_path: pathlib.Path, output_file_path: pathlib.Path) -> SiteContext:
    # Get current time for build date
    now = datetime.datetime.now(datetime.timezone.utc)

    return SiteContext(
        cfg=config,
        ctx=SimpleNamespace(
            output_file_path=output_file_path,
            site_dir_path=site_dir_path,
            current_year=now.year,
            date_now=now,
            css_file_path=site_dir_path / RESOURCES_DIR_NAME / CSS_FILE_NAME,
            favicon_path=site_dir_path / RESOURCES_DIR_NAME / FAVICON_FILE_NAME,
            index_path=site_dir_path / INDEX_TEMPLATE_NAME,
            # Return the URL by joining the global URL with the relative path
            request_path=full_site_url_to_resource(config.site_url, site_dir_path, output_file_path),
            site_description="Japanese subtitles for Japanese anime, dramas, TV shows, and movies",
            site_title="Japanese subtitles - AJATT",
            site_author="Tatsumoto Ren",
            site_keywords="japanese, subtitles, anime, TV, dramas, AJATT",
        ),
    )
