# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib as _pathlib

PROG_NAME = "kitsunekko-tools"
SETTINGS_FILE_NAME = "kitsunekko-tools.toml"
KITSUNEKKO_DOMAIN_URL = "https://kitsunekko.net"
REPO = _pathlib.Path(__file__).parent.absolute()
IGNORE_FILENAME = ".kitsuignore"
UPDATED_FILENAME = ".updated"

__all__ = [name for name in globals() if name.isupper()]
