# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import pathlib
import subprocess
import sys

import fire

from kitsunekko_tools import ApiSyncClient, KitsuScrapper
from kitsunekko_tools.__version__ import __version__
from kitsunekko_tools.common import KitsuError, KitsuException
from kitsunekko_tools.config import Config, ConfigFileNotFoundError
from kitsunekko_tools.consts import PROG_NAME
from kitsunekko_tools.filesystem import extract_archives
from kitsunekko_tools.ignore import (
    add_all_files_to_ignore_list,
    add_file_to_ignore_list,
)
from kitsunekko_tools.mega_upload import mega_upload
from kitsunekko_tools.sanitize import sanitize_directories, delete_empty_directories, delete_trash_dirs
from kitsunekko_tools.website.website import WebSiteBuilder, build_website


class ConfigCli:
    """
    Manage config.
    """

    _config: Config

    def __init__(self, config: Config) -> None:
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

    def __init__(self, config: Config) -> None:
        self._config = config

    def add(self, path_to_file: str) -> None:
        """
        Add a new ignore rule.
        """
        if not path_to_file:
            raise KitsuError("Nothing to add.")
        try:
            cfg = self._config.data()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            add_file_to_ignore_list(cfg=cfg, path_to_file=pathlib.Path(path_to_file).resolve())

    def add_all(self) -> None:
        """
        Update all ignore lists across the entire repository and add missing files.
        """
        try:
            cfg = self._config.data()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            add_all_files_to_ignore_list(cfg)


class Application:
    """
    A set of scripts for creating a local kitsunekko mirror.

    :param version: Print version and exit.
    :param config_path: Alternative path to the config file.
    """

    def __init__(self, version: bool = False, config_path: str | None = None) -> None:
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

    async def sync(
        self, full: bool = False, api: bool = False, ignore_dir_mod_times: bool = False, accept_file_types: str = ""
    ) -> None:
        """
        Download everything from Kitsunekko to a local folder.

        Args:
            full: Do a full sync. Ignore the 'skip_older' setting.
            api: Use the API to access the contents.
            ignore_dir_mod_times: Ignore modification times of directories when using the API.
            accept_file_types: a comma separated list of file types to download. If not set, use the value set in the config file.
        """

        config = self._config.data()
        if accept_file_types:
            config = dataclasses.replace(config, allowed_file_types=frozenset(accept_file_types.split(",")))

        if api:
            s = ApiSyncClient(config=config, full_sync=full, ignore_dir_mod_times=ignore_dir_mod_times)
        else:
            s = KitsuScrapper(config=config, full_sync=full)

        await s.sync_all()

    def upload(self) -> None:
        """
        Upload the local folder to mega.nz.
        The ~/.megarc file must exist.
        """
        try:
            mega_upload(self._config.data())
        except KitsuException as ex:
            print(ex.what)

    def sanitize(self, empty: bool = False, trash: bool = False) -> None:
        """
        Rename directories if they have prohibited names.
        Args:
            empty: Delete empty directories.
            trash: Delete trash directories.
        """
        cfg = self._config.data()

        if empty:
            delete_empty_directories(cfg)
        elif trash:
            delete_trash_dirs(cfg)
        else:
            sanitize_directories(cfg)

    def build(self) -> None:
        """
        Build website.
        """
        try:
            data = self._config.data()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            build_website(data)

    def copy_site_resources(self) -> None:
        try:
            data = self._config.data()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            b = WebSiteBuilder(data)
            b.copy_site_resources()

    def git(self, *args) -> None:
        """
        Run git commands in the destination directory.
        This doesn't make sense if the destination is not in a git repository.
        """
        try:
            data = self._config.data()
        except ConfigFileNotFoundError as ex:
            print(ex.what)
        else:
            ret = subprocess.run(
                args=("git", *args),
                stdout=sys.stdout,
                stderr=sys.stderr,
                check=False,
                cwd=data.destination,
            )
            sys.exit(ret.returncode)

    def extract_archives(self) -> None:
        """
        Find archives and extract them.
        """
        extract_archives(self._config.data())


def main() -> None:
    try:
        fire.Fire(Application)
    except KitsuException as ex:
        print(ex.what)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted by the user.")


if __name__ == "__main__":
    main()
