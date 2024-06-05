# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html


PROG_NAME = "kitsunekko-tools"
SETTINGS_FILE_NAME = f"{PROG_NAME}.toml"
KITSUNEKKO_DOMAIN_URL = "https://kitsunekko.net"
IGNORE_FILENAME = ".kitsuignore"
INFO_FILENAME = ".kitsuinfo.json"
TRASH_DIR_NAME = "extra"

__all__ = [name for name in globals() if name.isupper()]
