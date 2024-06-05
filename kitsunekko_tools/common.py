# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import re


class KitsuException(Exception, abc.ABC):
    @property
    @abc.abstractmethod
    def what(self) -> str:
        raise NotImplementedError()


RE_FILENAME_PROHIBITED = re.compile(r"[ _\\\n\t\r#\[\]{}<>^*/:`?'|]+", flags=re.MULTILINE | re.IGNORECASE)
RE_MULTI_SPACE = re.compile(r" {2,}", flags=re.MULTILINE | re.IGNORECASE)


def fs_name_strip(name: str) -> str:
    name = name.replace(":", ".")
    name = name.replace("??", "2")
    name = name.replace("||", "2")
    name = re.sub(RE_FILENAME_PROHIBITED, " ", name)
    name = re.sub(RE_MULTI_SPACE, " ", name)
    return name.strip()
