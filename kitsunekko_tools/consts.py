# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib
import typing
from collections.abc import Sequence

S = typing.Final[str]
P = typing.Final[pathlib.Path]
SS = typing.Final[Sequence[str]]

PROG_NAME: S = "kitsunekko-tools"
SETTINGS_FILE_NAME: S = f"{PROG_NAME}.toml"
KITSUNEKKO_DOMAIN_URL: S = "https://kitsunekko.net"
IGNORE_FILENAME: S = ".kitsuignore"
INFO_FILENAME: S = ".kitsuinfo.json"
TRASH_DIR_NAME: S = "extra"

THIS_DIR: P = pathlib.Path(__file__).resolve().parent
BUNDLED_RESOURCES_DIR: P = THIS_DIR / "example_catalog" / "resources"
BUNDLED_TEMPLATES_DIR: P = BUNDLED_RESOURCES_DIR.with_name("templates")
BUNDLED_SUBTITLES_DIR: P = BUNDLED_RESOURCES_DIR.with_name("subtitles")

SUBTITLE_FILE_TYPES: SS = ("srt", "ass", "ssa")
ARCHIVE_FILE_TYPES: SS = ("zip", "rar", "7z")

assert BUNDLED_RESOURCES_DIR.is_dir()
assert BUNDLED_TEMPLATES_DIR.is_dir()
assert BUNDLED_SUBTITLES_DIR.is_dir()

# Default MIME type for files whose extension cannot be guessed.
# Matches the IANA fallback for "unknown binary" content.
FALLBACK_MIME_TYPE: S = "application/octet-stream"

# Sitemap namespace used in the sitemap Jinja template.
SITEMAP_NS: S = "http://www.sitemaps.org/schemas/sitemap/0.9"

__all__ = [name for name in globals() if name.isupper()]
