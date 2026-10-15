# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import functools
import http.server
import os
import subprocess
import sys

from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.website.context import make_site_dir_path


def system_browser() -> str:
    """Return the browser command from $BROWSER or fall back to xdg-open."""
    # substitute xdg-open instead of an empty string or None.
    return os.environ.get("BROWSER") or "xdg-open"


def open_page_in_browser(url: str) -> subprocess.Popen[bytes] | None:
    """Open a URL in the system browser without blocking the command line."""
    try:
        return subprocess.Popen(
            (system_browser(), url),
            stderr=subprocess.STDOUT,
            stdout=subprocess.DEVNULL,
            shell=False,
            start_new_session=True,  # The browser should survive a server keyboard interrupt.
        )
    except OSError as ex:
        print(f"Warning: could not open the browser: {ex}", file=sys.stderr)


def make_server(config: KitsuConfig) -> http.server.ThreadingHTTPServer:
    """Create a threaded HTTP server for the generated site using configured network settings."""
    return http.server.ThreadingHTTPServer(
        server_address=(config.server_bind_address, config.server_bind_port),
        RequestHandlerClass=functools.partial(
            http.server.SimpleHTTPRequestHandler,
            directory=make_site_dir_path(config),
        ),
    )


def server_config(config: KitsuConfig, *, address: str | None = None, port: int | None = None) -> KitsuConfig:
    """Return configuration with command-line server overrides applied."""
    return dataclasses.replace(
        config,
        server_bind_address=config.server_bind_address if address is None else address,
        server_bind_port=config.server_bind_port if port is None else port,
    )


def serve_site(
    config: KitsuConfig,
    *,
    address: str | None = None,
    port: int | None = None,
    launch_browser: bool = True,
) -> None:
    """Serve the generated site and optionally open its local URL in the system browser."""
    config = server_config(config, address=address, port=port)
    server = make_server(config)
    try:
        print(f"Serving {make_site_dir_path(config)} at {config.server_url}")
        if launch_browser:
            open_page_in_browser(config.server_url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt.")
    finally:
        server.server_close()
        print("Server stopped.")
