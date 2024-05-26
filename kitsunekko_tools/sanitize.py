# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
def sanitize_directories(config: KitsuConfig) -> None:
    for directory in data.destination.iterdir():
        sanitized_name = fs_name_strip(directory.name)
        if sanitized_name == directory.name:
            continue
        new_path = directory.parent / sanitized_name
        if new_path.exists():
            raise ValueError(f"{directory.name}: already exists: {new_path}")
        else:
            directory.rename(new_path)
