# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib

PROG_NAME = "kitsunekko-tools"
SETTINGS_FILE_NAME = f"{PROG_NAME}.toml"
KITSUNEKKO_DOMAIN_URL = "https://kitsunekko.net"
IGNORE_FILENAME = ".kitsuignore"
INFO_FILENAME = ".kitsuinfo.json"
TRASH_DIR_NAME = "extra"

THIS_DIR = pathlib.Path(__file__).resolve().parent
BUNDLED_RESOURCES_DIR = THIS_DIR / "example_catalog" / "resources"
BUNDLED_TEMPLATES_DIR = BUNDLED_RESOURCES_DIR.with_name("templates")
BUNDLED_SUBTITLES_DIR = BUNDLED_RESOURCES_DIR.with_name("subtitles")

SUBTITLE_FILE_TYPES = ("srt", "ass", "ssa")
ARCHIVE_FILE_TYPES = ("zip", "rar", "7z")

assert BUNDLED_RESOURCES_DIR.is_dir()
assert BUNDLED_TEMPLATES_DIR.is_dir()
assert BUNDLED_SUBTITLES_DIR.is_dir()

__all__ = [name for name in globals() if name.isupper()]
