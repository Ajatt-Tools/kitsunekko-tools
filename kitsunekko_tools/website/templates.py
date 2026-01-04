# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import datetime
import enum
import pathlib
from typing import Any

import jinja2
from beartype import beartype
from jinja2 import Environment, FileSystemLoader, select_autoescape

from kitsunekko_tools.website.context import SiteContext
from kitsunekko_tools.website.filesystem import (
    as_relative_to,
    full_site_url_to_resource,
)

DATE_FORMAT_FULL = "%a, %d %b %Y %H:%M:%S %z"
DATE_FORMAT_UNIX = "%s"
DATE_ALL_POSTS_HEADER = "%B %Y"
DATE_ALL_POSTS_POST = "%B %d, %Y"  #  January 08, 2025

from kitsunekko_tools.config import KitsuConfig


@beartype
def timestamp_int(dt: datetime.datetime) -> int:
    return int(dt.timestamp())


@beartype
def strftime_filter(dt: datetime.datetime, format_str: str) -> str:
    return dt.strftime(format_str)


@beartype
def date_allposts_filter(dt: datetime.datetime) -> str:
    return strftime_filter(dt, DATE_ALL_POSTS_HEADER)


@beartype
def date_allposts_post_filter(dt: datetime.datetime) -> str:
    return strftime_filter(dt, DATE_ALL_POSTS_POST)


@beartype
def date_full_filter(dt: datetime.datetime) -> str:
    return strftime_filter(dt, DATE_FORMAT_FULL)


@beartype
def as_subtitle_download_url(path: pathlib.Path, cfg: KitsuConfig) -> str:
    """
    Make a URL like this: https://raw.githubusercontent.com/Ajatt-Tools/kitsunekko-mirror/refs/heads/main/subtitles/ShowName/file.srt
    """
    return full_site_url_to_resource(
        global_url=cfg.raw_subtitles_dir_url,
        site_dir=cfg.destination,
        file_path=path,
    )


def size_bytes_to_human(size_bytes: int) -> str:
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


@beartype
def no_trailing_slash(url: str) -> str:
    return url.rstrip(r"\/")


@beartype
class TemplateType(enum.Enum):
    blog = enum.auto()
    landing = enum.auto()


@beartype
class JinjaEnvHolder:
    @beartype
    def __init__(self, config: KitsuConfig, templates_dir_path: pathlib.Path, site_dir_path: pathlib.Path) -> None:
        self._cfg = config
        self._templates_dir_path = templates_dir_path
        self._site_dir_path = site_dir_path
        self._template_env = self.create_tmpl_env()

    @property
    def template_env(self) -> jinja2.Environment:
        return self._template_env

    @beartype
    def create_tmpl_env(self) -> jinja2.Environment:
        """Create a Jinja2 template environment."""
        env = Environment(
            loader=FileSystemLoader(self._templates_dir_path),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=jinja2.StrictUndefined,
        )

        # Add custom filter for converting absolute paths to relative paths
        # This filter will be used in templates like: {{ '/img/logo.webp'| relative_path }}
        @beartype
        def relative_filter(resource_path: pathlib.Path, html_file_path: pathlib.Path) -> str:
            return as_relative_to(html_file_path, resource_path)

        @beartype
        def relative_to_site_dir_filter(path: str | pathlib.Path) -> str:
            return str(pathlib.Path(path).relative_to(self._site_dir_path))

        @beartype
        def full_url_filter(path: str | pathlib.Path) -> str:
            return full_site_url_to_resource(
                global_url=self._cfg.site_url,
                site_dir=self._site_dir_path,  # _site
                file_path=pathlib.Path(path),
            )

        @beartype
        def as_abs_path_to_site_dir_filter(path: str | pathlib.Path) -> pathlib.Path:
            return self._site_dir_path.resolve().joinpath(path)

        @beartype
        def as_subtitle_download_url_filter(path: pathlib.Path) -> str:
            """
            Make a URL like this: https://raw.githubusercontent.com/Ajatt-Tools/kitsunekko-mirror/refs/heads/main/subtitles/ShowName/file.srt
            """
            return as_subtitle_download_url(path, self._cfg)

        @beartype
        def as_subtitle_git_url_filter(path: pathlib.Path) -> str:
            """
            Make a URL like this: https://github.com/Ajatt-Tools/kitsunekko-mirror/tree/main/subtitles/ShowName
            """
            return full_site_url_to_resource(
                global_url=self._cfg.git_subtitles_dir_url,
                site_dir=self._cfg.destination,
                file_path=path,
            )

        # Add custom filters for file paths and converting paths to HTML
        env.filters["as_relative_to"] = relative_filter
        env.filters["relative_to_site_dir"] = relative_to_site_dir_filter
        env.filters["as_full_url"] = full_url_filter
        env.filters["as_abs_path_to_site_dir"] = as_abs_path_to_site_dir_filter
        env.filters["as_subtitle_download_url"] = as_subtitle_download_url_filter
        env.filters["as_subtitle_git_url"] = as_subtitle_git_url_filter

        # Add custom filter for integer timestamps
        env.filters["timestamp_int"] = timestamp_int
        env.filters["no_trailing_slash"] = no_trailing_slash
        env.filters["strftime"] = strftime_filter
        env.filters["date_allposts"] = date_allposts_filter
        env.filters["date_allposts_post"] = date_allposts_post_filter
        env.filters["date_full"] = date_full_filter

        # Files size
        env.filters["size_bytes_to_human"] = size_bytes_to_human

        return env


@beartype
def render_template(template_name: str, context: SiteContext, template_env: Environment) -> str:
    """Render a template with the given context."""
    template = template_env.get_template(template_name)
    return template.render(dataclasses.asdict(context))
