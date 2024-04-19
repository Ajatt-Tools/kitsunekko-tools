# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html


import pathlib

PROG = "kitsunekko-tools"
SETTINGS = "settings.json"
DOMAIN = "https://kitsunekko.net"
REPO = pathlib.Path(__file__).parent.absolute()
IGNORE_FILENAME = ".kitsuignore"
UPDATED_FILENAME = ".updated"

del pathlib
