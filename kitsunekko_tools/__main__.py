# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import asyncio

from kitsunekko_tools.kitsunekko_dl import async_main


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
