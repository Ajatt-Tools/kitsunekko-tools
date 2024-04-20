# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import fire

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import ConfigFileNotFoundError, KitsuConfig, get_config
from kitsunekko_tools.download import Sync
from kitsunekko_tools.ignore import IgnoreList, IgnoreListException
from kitsunekko_tools.mega_upload import mega_upload


class ConfigCli:
    """
    Manage config file.
    """

    @staticmethod
    def create() -> None:
        """
        Create an example config file in the default location, if it does not exist.
        """
        try:
            data, location = get_config()
        except ConfigFileNotFoundError:
            config_file_path = KitsuConfig.default_location()
            config_file_path.parent.mkdir(exist_ok=True, parents=True)
            config_file_path.write_text(KitsuConfig().as_toml_str())
            print(f"Created config file: {config_file_path}")
        else:
            print(f"File already exists: {location}")

    @staticmethod
    def locate() -> None:
        """
        Print path to the config file, if it exists.
        """
        try:
            data, location = get_config()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            print(location)

    @staticmethod
    def show() -> None:
        """
        Show the content of the config file, if it exists.
        """
        try:
            data, location = get_config()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            print(data.as_toml_str())


class IgnoreCli:
    """
    Manage the list of ignore patterns.
    """

    def __init__(self, ignore_list: IgnoreList):
        self._ignore_list = ignore_list

    def locate(self) -> None:
        """
        Print path to the ignore file.
        """
        print(self._ignore_list.ignore_filepath)

    def show(self) -> None:
        """
        Print the list of ignore rules as Unix shell-style wildcards.
        """
        print("\n".join(self._ignore_list.patterns()))

    def add(self, pattern: str) -> None:
        """
        Add a new ignore rule.
        """
        if pattern:
            self._ignore_list.add(str(pattern))
            print(f"File written: {self._ignore_list.path()}")
        else:
            print("Nothing to add.")


class Application:
    """
    A set of scripts for creating a local kitsunekko mirror.
    """

    @staticmethod
    def config() -> ConfigCli:
        """
        Manage config file.
        """
        return ConfigCli()

    @staticmethod
    def destination() -> None:
        """
        Print path to destination directory.
        """
        try:
            data, location = get_config()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            print(data.destination)

    @staticmethod
    def ignore():
        """
        Manage the list of ignore patterns.
        """
        try:
            return IgnoreCli(IgnoreList())
        except IgnoreListException as ex:
            print(ex.what)

    @staticmethod
    async def sync():
        """
        Download everything from Kitsunekko to a local folder.
        """
        try:
            s = Sync()
        except KitsuException as ex:
            print(ex.what)
        else:
            await s.sync_all()

    @staticmethod
    def upload():
        """
        Upload the local folder to mega.nz.
        The ~/.megarc file must exist.
        """
        try:
            mega_upload(get_config().data)
        except KitsuException as ex:
            print(ex.what)


def main() -> None:
    try:
        fire.Fire(Application)
    except KeyboardInterrupt:
        print("Aborted by the user.")


if __name__ == "__main__":
    main()
