# SPDX-FileCopyrightText: Copyright (c) 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`HTTPServer`
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
    from typing import Any
except ImportError:
    pass

from adafruit_httpserver.webapplication import WebApplication
from adafruit_httpserver.webservergateway import WebServerGateway

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
        self.application = WebApplication("/", debug=False)
        self.gateway = WebServerGateway(self.application, socket_source, debug=False)

    def route(self, path: str, method: str = "GET"):
        """Decorator used to add a route.

        :param str path: filename path
        :param str method: HTTP method: "GET", "POST", etc.

        A callable route should accept the following args
            (request: HTTPRequest)
        A callable route should return an HTTPResponse object
            -> HTTPResponse:

        Example::

            @server.route(path, method)
            def route_func(request: HTTPRequest) -> HTTPResponse:
                return HTTPResponse(body="hello world")
        """
        methods = [method]
        rule = path
        return lambda func: self.application.register_route(methods, rule, func)

    def serve_forever(self, host: str, port: int = 80) -> None:
        """Wait for HTTP requests at the given host and port. Does not return.

        :param str host: host name or IP address
        :param int port: port
        :param str root: root directory to serve files from
        """
        self.gateway.serve_forever(host, port)

    def start(self, host: str, port: int = 80) -> None:
        """
        Start the HTTP server at the given host and port. Requires calling
        poll() in a while loop to handle incoming requests.

        :param str host: host name or IP address
        :param int port: port
        :param str root: root directory to serve files from
        """
        self.gateway.start_server(host, port)

    def poll(self):
        """
        Call this method inside your main event loop to get the server to
        check for new incoming client requests. When a request comes in,
        the application callable will be invoked.
        """
        self.gateway.poll_server()
