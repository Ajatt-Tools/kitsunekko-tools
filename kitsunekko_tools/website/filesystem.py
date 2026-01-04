# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
import urllib.parse
from collections.abc import Iterable

from beartype import beartype

from kitsunekko_tools.common import KitsuError


@beartype
def walk_parents(dir_or_file_path: str | pathlib.Path) -> Iterable[pathlib.Path]:
    current_dir = pathlib.Path(dir_or_file_path).absolute()
    if current_dir.is_dir():
        yield current_dir
    while not current_dir.samefile(current_dir.parent):
        yield current_dir.parent
        current_dir = current_dir.parent


@beartype
def find_file_in_parents(file_name: str, start_from: str = ".") -> pathlib.Path:
    for parent_dir in walk_parents(start_from):
        if (path := parent_dir.joinpath(file_name)).is_file():
            return path
    raise FileNotFoundError(f"couldn't find file '{file_name}'")


@beartype
def as_relative_to(html_file: pathlib.Path, css_or_js_include: str | pathlib.Path) -> str:
    """Calculate relative path from HTML file to CSS/JS include.

    Examples:
    as_relative_to(pathlib.Path("blog/post.html"), "blog/post.html") -> "post.html"
    as_relative_to(pathlib.Path("blog/post.html"), "blog/res/blog.css") -> "res/blog.css"
    as_relative_to(pathlib.Path("blog/post.html"), "res/blog.css") -> "../res/blog.css"
    as_relative_to(pathlib.Path("post.html"), "res/blog.css") -> "res/blog.css"
    as_relative_to(pathlib.Path("articles/post.html"), "css/blog.css") -> "../css/blog.css"
    """
    # Convert string path to Path object
    html_file = html_file.resolve()
    include_path = pathlib.Path(css_or_js_include).resolve()
    # Get the directory of the HTML file
    html_dir = html_file.parent

    # Find common prefix length
    common_prefix_len = 0
    for i in range(min(len(html_dir.parts), len(include_path.parts))):
        if html_dir.parts[i] == include_path.parts[i]:
            common_prefix_len += 1
        else:
            break

    # Calculate how many levels up we need to go from html_dir
    levels_up = len(html_dir.parts) - common_prefix_len

    # Calculate the remaining path from the common prefix
    remaining_path_parts = include_path.parts[common_prefix_len:]

    # Build the relative path
    if levels_up > 0:
        relative_path = pathlib.Path("../" * levels_up)
        if remaining_path_parts:
            relative_path = relative_path / pathlib.Path(*remaining_path_parts)
    else:
        # No levels up needed, use remaining path directly
        relative_path = pathlib.Path(*remaining_path_parts) if remaining_path_parts else pathlib.Path(".")

    return relative_path.as_posix()


def full_site_url_to_resource(global_url: str, site_dir: pathlib.Path, file_path: pathlib.Path) -> str:
    """Get the URL for a post.

    Constructs the full URL by combining the global URL with the relative path
    from the site directory to the post file.
    """
    # Convert to relative path from site directory
    relative_path = str(file_path.resolve().relative_to(site_dir))
    # Return the URL by joining the global URL with the relative path
    if relative_path.startswith("/"):
        raise KitsuError("relative path can't start with a slash.")
    return f"{global_url.rstrip('/')}/{urllib.parse.quote(relative_path)}"
