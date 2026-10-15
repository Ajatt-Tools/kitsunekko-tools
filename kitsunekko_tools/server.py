# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import functools
import http.server
import os
import shlex
import subprocess
import sys

from kitsunekko_tools.common import KitsuError
from kitsunekko_tools.config import KitsuConfig
from kitsunekko_tools.consts import DEFAULT_SERVER_BIND_ADDRESS
from kitsunekko_tools.website.context import make_site_dir_path


def system_browser() -> str:
    """Return the system browser command from $BROWSER or fall back to xdg-open."""
    # Substitute xdg-open instead of an unset, empty, or whitespace-only command.
    return os.environ.get("BROWSER", "").strip() or "xdg-open"


def open_page_in_browser(url: str) -> subprocess.Popen[bytes] | None:
    """Launch the browser without waiting, warning only about startup failures."""
    try:
        return subprocess.Popen(
            # Parse quoted arguments without allowing shell expansion or command execution.
            # Support env vars like: BROWSER="firefox --new-window"
            (*shlex.split(system_browser()), url),
            stderr=subprocess.STDOUT,
            stdout=subprocess.DEVNULL,
            shell=False,
            start_new_session=True,  # The browser should survive a server keyboard interrupt.
        )
    except (OSError, ValueError) as ex:
        # shlex.split() raises ValueError for malformed quoting.
        print(f"Warning: could not open the browser: {ex}", file=sys.stderr)


def make_server(config: KitsuConfig) -> http.server.ThreadingHTTPServer:
    """Create an IPv4 HTTP server, rejecting unsupported IPv6 bind addresses."""
    # ThreadingHTTPServer uses AF_INET. Reject IPv6 before exposing a low-level socket error.
    if ":" in config.server_bind_address:
        raise KitsuError("The catalog server supports IPv4 only. Use an IPv4 address or hostname.")
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


def run_server(server: http.server.ThreadingHTTPServer, config: KitsuConfig, *, launch_browser: bool) -> None:
    """Run the bound server, handling interruption while leaving cleanup to the caller."""
    try:
        print(f"Serving {make_site_dir_path(config)} at {server_browser_url(server)}")
        if launch_browser:
            open_page_in_browser(server_browser_url(server))
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt.")
    finally:
        print("Server stopped.")


def serve_site(
    config: KitsuConfig,
    *,
    address: str | None = None,
    port: int | None = None,
    launch_browser: bool = True,
) -> None:
    """Serve the generated site and optionally open its local URL in the system browser."""
    config = server_config(config, address=address, port=port)
    with make_server(config) as server:
        run_server(server, config=config, launch_browser=launch_browser)


def server_browser_url(server: http.server.ThreadingHTTPServer) -> str:
    """Return a navigable IPv4 URL using the listener's actual assigned port."""
    address, port = server.server_address
    # Use loopback for wildcard listeners rather than browser-specific wildcard handling.
    host = DEFAULT_SERVER_BIND_ADDRESS if address == "0.0.0.0" else address
    return f"http://{host}:{port}/"
