# SPDX-FileCopyrightText: Copyright (c) 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_httpserver`
================================================================================

Simple HTTP Server for CircuitPython


* Author(s): Dan Halbert

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
"""

try:
    from typing import Any, Callable
except ImportError:
    pass

from adafruit_httpserver.httprequest import _HTTPRequest
from adafruit_httpserver.httpresponse import HTTPResponse
from adafruit_httpserver.httpstatus import HTTPStatus

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_HTTPServer.git"


class HTTPServer:
    """A basic socket-based HTTP server."""

    def __init__(self, socket_source: Any) -> None:
        # TODO: Use a Protocol for the type annotation.
        # The Protocol could be refactored from adafruit_requests.
        """Create a server, and get it ready to run.

        :param socket: An object that is a source of sockets. This could be a `socketpool`
          in CircuitPython or the `socket` module in CPython.
        """
        self._buffer = bytearray(1024)
        self.routes = {}
        self._socket_source = socket_source
        self._sock = None
        self.root_path = "/"

    def route(self, path: str, method: str = "GET"):
        """Decorator used to add a route.

        :param str path: filename path
        :param str method: HTTP method: "GET", "POST", etc.

        Example::

            @server.route(path, method)
            def route_func(request):
                return HTTPResponse(body="hello world")
        """

        def route_decorator(func: Callable) -> Callable:
            self.routes[_HTTPRequest(path, method)] = func
            return func

        return route_decorator

    def serve_forever(self, host: str, port: int = 80, root: str = "") -> None:
        """Wait for HTTP requests at the given host and port. Does not return.

        :param str host: host name or IP address
        :param int port: port
        :param str root: root directory to serve files from
        """
        self.start(host, port, root)

        while True:
            try:
                self.poll()
            except OSError:
                continue

    def start(self, host: str, port: int = 80, root: str = "") -> None:
        """
        Start the HTTP server at the given host and port. Requires calling
        poll() in a while loop to handle incoming requests.

        :param str host: host name or IP address
        :param int port: port
        :param str root: root directory to serve files from
        """
        self.root_path = root

        self._sock = self._socket_source.socket(
            self._socket_source.AF_INET, self._socket_source.SOCK_STREAM
        )
        self._sock.bind((host, port))
        self._sock.listen(10)

    def poll(self):
        """
        Call this method inside your main event loop to get the server to
        check for new incoming client requests. When a request comes in,
        the application callable will be invoked.
        """
        conn, _ = self._sock.accept()
        with conn:
            length, _ = conn.recvfrom_into(self._buffer)

            request = _HTTPRequest(raw_request=self._buffer[:length])

            # If a route exists for this request, call it. Otherwise try to serve a file.
            route = self.routes.get(request, None)
            if route:
                response = route(request)
            elif request.method == "GET":
                response = HTTPResponse(filename=request.path, root=self.root_path)
            else:
                response = HTTPResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)

            response.send(conn)
