# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import sys

import fire

from kitsunekko_tools.__version__ import __version__
from kitsunekko_tools.api_access.download import ApiSyncClient
from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import ConfigFileNotFoundError, Config, KitsuConfig
from kitsunekko_tools.consts import PROG_NAME
from kitsunekko_tools.ignore import IgnoreList
from kitsunekko_tools.mega_upload import mega_upload
from kitsunekko_tools.scrapper.download import KitsuScrapper


class ConfigCli:
    """
    Manage config.
    """

    _config: Config

    def __init__(self, config: Config):
        self._config = config

    def create(self) -> None:
        """
        Create an example config file in the default or user-specified location, if it does not exist.
        """
        try:
            location = self._config.file_path()
        except ConfigFileNotFoundError:
            location = self._config.create_config_file()
            print(f"Created config file: {location}")
        else:
            print(f"File already exists: {location}")

    def locate(self) -> None:
        """
        Print path to the config file, if it exists.
        """
        try:
            location = self._config.file_path()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            print(location)

    def show(self) -> None:
        """
        Show the content of the config file, if it exists.
        """
        try:
            data = self._config.data()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            print(data.as_toml_str())


class IgnoreCli:
    """
    Manage the list of ignore patterns.
    """

    _config: Config

    def __init__(self, config: Config):
        self._config = config

    def _get_list(self) -> IgnoreList:
        return IgnoreList(self._config.data())

    def locate(self) -> None:
        """
        Print path to the ignore file.
        """
        print(self._get_list().ignore_filepath)

    def show(self) -> None:
        """
        Print the list of ignore rules as Unix shell-style wildcards.
        """
        print("\n".join(self._get_list().patterns()))

    def add(self, pattern: str) -> None:
        """
        Add a new ignore rule.
        """
        if pattern:
            ignore_list = self._get_list()
            ignore_list.add(str(pattern))
            ignore_list.commit()
            print(f"File written: {ignore_list.path()}")
        else:
            print("Nothing to add.")


def get_client(api: bool, config: KitsuConfig, full_sync: bool) -> ApiSyncClient | KitsuScrapper:
    return (ApiSyncClient if api else KitsuScrapper)(config=config, full_sync=full_sync)


class Application:
    """
    A set of scripts for creating a local kitsunekko mirror.

    :param version: Print version and exit.
    :param config_path: Alternative path to the config file.
    """

    def __init__(self, version: bool = False, config_path: str | None = None):
        self._config = Config(config_path)
        self.config = ConfigCli(self._config)
        self.ignore = IgnoreCli(self._config)
        if version:
            # handle ktools --version
            sys.exit(self.version())

    @staticmethod
    def version() -> None:
        """
        Print version and exit.
        """
        print(f"{PROG_NAME} version: {__version__}")

    def destination(self) -> None:
        """
        Print path to destination directory.
        """
        try:
            data = self._config.data()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            print(data.destination)

    async def sync(self, full: bool = False, api: bool = False) -> None:
        """
        Download everything from Kitsunekko to a local folder.

        :param full: Do a full sync. Ignore the 'skip_older' setting.
        :param api: Use the API to access the contents.
        """
        try:
            s = get_client(api=api, config=self._config.data(), full_sync=full)
        except KitsuException as ex:
            print(ex.what)
        else:
            await s.sync_all()

    def upload(self):
        """
        Upload the local folder to mega.nz.
        The ~/.megarc file must exist.
        """
        try:
            mega_upload(self._config.data())
        except KitsuException as ex:
            print(ex.what)


def main() -> None:
    try:
        fire.Fire(Application)
    except KitsuException as ex:
        print(ex.what)
    except KeyboardInterrupt:
        print("\nAborted by the user.")


if __name__ == "__main__":
    main()
