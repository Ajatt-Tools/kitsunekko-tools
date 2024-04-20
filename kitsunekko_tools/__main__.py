# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import fire

from kitsunekko_tools.config import ConfigFileNotFoundError, KitsuConfigData


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
            data, location = KitsuConfigData.read()
        except ConfigFileNotFoundError:
            config_file_path = KitsuConfigData.default_location()
            config_file_path.parent.mkdir(exist_ok=True, parents=True)
            config_file_path.write_text(KitsuConfigData().as_toml_str())
            print(f"Created config file: {config_file_path}")
        else:
            print(f"File already exists: {location}")

    @staticmethod
    def locate() -> None:
        """
        Print path to the config file, if it exists.
        """
        try:
            data, location = KitsuConfigData.read()
        except ConfigFileNotFoundError as ex:
            print(ex.describe())
        else:
            print(location)

    @staticmethod
    def show() -> None:
        """
        Show the content of the config file, if it exists.
        """
        try:
            data, location = KitsuConfigData.read()
        except ConfigFileNotFoundError as ex:
            print(ex.describe())
        else:
            print(data.as_toml_str())


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
            data, location = KitsuConfigData.read()
        except ConfigFileNotFoundError as ex:
            print(ex.describe())
        else:
            print(data.destination)


def main() -> None:
    fire.Fire(Application)


if __name__ == "__main__":
    main()
