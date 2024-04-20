# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html


import pathlib

PROG_NAME = "kitsunekko-tools"
SETTINGS_FILE_NAME = "kitsunekko-tools.json"
KITSUNEKKO_DOMAIN_URL = "https://kitsunekko.net"
REPO = pathlib.Path(__file__).parent.absolute()
IGNORE_FILENAME = ".kitsuignore"
UPDATED_FILENAME = ".updated"

del pathlib
