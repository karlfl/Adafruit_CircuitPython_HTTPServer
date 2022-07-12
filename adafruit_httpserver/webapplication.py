# SPDX-FileCopyrightText: Copyright (c) 2022 Karl Fleischmann
# SPDX-License-Identifier: MIT
"""
================================================================================
`HTTPServer`
Simple Socket Based Web (HTTP) Server for CircuitPython that implements applicaton
portion of the PEP3333 standard

* Author(s): Karl Fleischmann

Implementation Notes
--------------------

Adapted from
    https://github.com/adafruit/Adafruit_CircuitPython_HTTPServer
    https://github.com/adafruit/Adafruit_CircuitPython_WSGI
    https://github.com/adafruit/Adafruit_CircuitPython_ESP32SPI

Limited Support of the following specs:
    https://www.rfc-editor.org/rfc/rfc2616.txt - HTTP/1.1
    https://datatracker.ietf.org/doc/html/draft-coar-cgi-v11-03 - CGI/1.1
    https://peps.python.org/pep-3333 - Python Web Server Gateway Interface (WSGI) v1.0.1

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
"""
try:
    from typing import Any, AnyStr, Callable, Optional, List, Dict, Tuple, Sequence
except ImportError:
    pass

import re

from adafruit_httpserver.httpstatus import HTTPStatus
from adafruit_httpserver.httprequest import HTTPRequest
from adafruit_httpserver.httpresponse import HTTPResponse

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/karlfl/WebServer.git"


class WebApplication:
    """
    The base WebApplication class.
    """

    def __init__(self, rootpath: str = None, debug: bool = False):
        """Create an application, and get it ready to run.

        :param str rootpath: the path to the root directory used for the application
        :param bool debug: If True, print debug messages to console
        """
        self._debug = debug
        self._routes = []
        self._variable_regex = re.compile("^<([a-zA-Z]+)>$")
        self._root_path = rootpath

    def __call__(self, environ: Dict[str, str], start_response: Callable):
        """
        Called whenever the server gets a request.
        The environ dict has details about the request per wsgi specification.
        Calls start_response with the response status string and headers as a list of tuples.
        Return a single item list with the item being your response data string.

        :param dict environ: the environment variables from the incoming request
        :param func start_response: the function to call to send the headers and
            start the response
        """
        response_bytes = b""
        try:
            # create a HTTPRequest object for the downstream route function to use
            request = HTTPRequest(environ)

            # find the appropriate route and function to use
            match = self.__match_route(request.path, request.method.upper())
            filepath = (self._root_path + request.path).replace("//", "/")
            if match:
                args, route = match
                try:
                    # call the route function that was found via match_route
                    response = route["func"](request, *args)
                except (ValueError, TypeError) as err:
                    raise RuntimeError(
                        "Proper HTTPResponse not returned by request handler for path "
                        + f"'{request.path}'"
                        + "\nINNER_EXCEPTION:"
                        + str(err)
                    ) from err
            elif request.method == "GET" and filepath != "/":
                # No route found but method is "GET", Try to serve a static file
                if self._debug:
                    print(f"No route found for {request.path}")
                    print("Trying to serve static file", filepath)
                response = HTTPResponse(filename=request.path, root=self._root_path)
            else:
                if self._debug:
                    print(
                        "No Route or File Found for",
                        f"{request.method} - {request.path}",
                    )
                response = HTTPResponse(
                    status=HTTPStatus.NOT_FOUND,
                    body=f"{HTTPStatus.NOT_FOUND} {request.path}\r\n",
                )

            # per the WSGI spec, the application must call start_response
            # before returning any data
            start_response(response.status, response.headers)

            # now return the response body or file data
            return [response.body]

        except ValueError as err:
            if self._debug:
                raise err
            if not self._debug:
                # if we're not debugging, just return a 500 error
                start_response(HTTPStatus.INTERNAL_SERVER_ERROR.value, [])

        return response_bytes

    def route(self, rule: str, methods: Optional[List[str]] = None) -> Callable:
        """
        A decorator to register a route rule with an endpoint function.
        if no methods are provided, default to GET

        A route callable should accept the following args:
            (HTTPRequest request)
        A route callable should return a HTTPResponse object:
            -> HTTPResponse:

        :param str rule: the url path for this callable route
        :param list methods: the list of HTTP methods to match for this route
        :return: the decorated function
        """
        if not methods:
            methods = ["GET"]
        return lambda func: self.register_route(methods, rule, func)

    def register_route(
        self, methods: List[str], rule: str, request_handler: Callable
    ) -> None:
        """Add a callable route to the list of routes."""
        regex = "^"
        rule_parts = rule.split("/")
        for part in rule_parts:
            var = self._variable_regex.match(part)
            if var:
                # If named capture groups ever become a thing, use this regex instead
                # regex += "(?P<" + var.group("var") + r">[a-zA-Z0-9_-]*)\/"
                regex += r"([a-zA-Z0-9\._-]+)\/"
            else:
                regex += part + r"\/"
        regex += "?$"  # make last slash optional and that we only allow full matches
        if self._debug:
            print(f"Adding route: {methods} {rule}")
        self._routes.append(
            (re.compile(regex), {"methods": methods, "func": request_handler})
        )

    def __match_route(
        self, path: str, method: str
    ) -> Optional[Tuple[Sequence[AnyStr], Dict[str, Any]]]:
        if self._debug:
            print(f"Searching {len(self._routes)} routes for {path}, {method}")
        for matcher, route in self._routes:
            path_match = matcher.match(path)
            method_match = method in route["methods"]
            if self._debug:
                print(f"Route: {path}, {method} - Match: {path_match}, {method_match}")
            if path_match and method_match:
                return path_match.groups(), route
        return None
