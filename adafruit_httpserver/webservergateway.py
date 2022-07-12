# SPDX-FileCopyrightText: Copyright (c) 2022 Karl Fleischmann
# SPDX-License-Identifier: MIT
"""
================================================================================
`HTTPServer`
Simple Socket Based Web (HTTP) Server for CircuitPython that implements server
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
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/karlfl/WebServer.git"

try:
    from typing import Any, Dict
except ImportError:
    pass

import io
import gc
from errno import EAGAIN, ECONNRESET

from adafruit_httpserver.webapplication import WebApplication
from adafruit_httpserver.httpstatus import HTTPStatus


class WebServerGateway:
    """A basic socket-based HTTP server."""

    def __init__(
        self,
        application: WebApplication,
        socket_source: Any,
        debug=False,
    ) -> None:
        """Create a server, and get it ready to run.

        :param callable application: the application callable to invoke when a request comes in.
        :param socket: An object that is a source of sockets. This could be a `socketpool`
            in CircuitPython or the `socket` module in CPython.
        :param bool debug: If True, print debug messages to the console.
        """
        # TODO: implement multiple applications listening on different ports
        self._debug = debug
        self._buffer = bytearray(1024)  # default buffer size for reading requests
        self._socket_source = socket_source
        self._socket = None
        self._host = None
        self._port: int = 80
        self._application = application
        self._response_headers = None
        self._response_status = HTTPStatus.OK

    def serve_forever(self, host: str, port: int = 80) -> None:
        """Wait for HTTP requests at the given host and port. Does not return.

        :param str host: host name or IP address
        :param int port: port

        """
        self.start_server(host, port)

        while True:
            try:
                """Process any inbound web requests"""
                self.poll_server()
            except OSError:
                continue

    def start_server(self, host: str, port: int = 80) -> None:
        """Start the HTTP server at the given host and port.

        :param str host: host name or IP address
        :param int port: port
        :param str root: root directory to serve files from
        """
        self._host = host
        self._port = port
        # prepare the TCP socket
        self._socket = self._socket_source.socket(
            self._socket_source.AF_INET, self._socket_source.SOCK_STREAM
        )
        self._socket.bind((self._host, self._port))
        self._socket.listen(1)

    def stop_server(self) -> None:
        """Stop the server."""
        if self._socket:
            self._socket.close()
            self._socket = None

    def poll_server(self):
        """
        Call this method inside your main event loop to get the server to
        check for new incoming client requests. When a request comes in,
        the application callable will be invoked.
        """
        if self._socket is None:
            raise Exception(
                "Server not started.  Call start_server before trying to poll."
            )

        conn, remote_address = self._socket.accept()
        if self._debug:
            print("Accepting connection from", remote_address)
        with conn:
            try:
                # Read the stream buffer from the client connection
                length, _ = conn.recvfrom_into(self._buffer)
                if self._debug:
                    print("Bytes received", length)

                # Parse full request data from the buffer
                request_text = self._buffer[:length].decode("utf8")

                # standardize line endings
                request_text = "\n".join(request_text.splitlines())
                # if self._debug:
                #     print(f"RawRequest ({length}):\n{request_text}")

                # Parse the request data into environment variables
                environ = self.__get_environ(request_text, remote_address)

                # call the application passing in the environ and callable to start the response
                result = self._application(environ, self._start_response)

                # send the response to the client
                self.__finish_response(conn, result)
            finally:
                if self._debug:
                    print("Closing connection")
                conn.close()

    def _start_response(self, status, headers):
        """
        The application callable will be given this method as the second param
        This is to be called before the application callable returns, to signify
        the response can be started with the given status and headers.

        :param string status: a status string including the code and reason. ex: "200 OK"
        :param list response_headers: a list of tuples to represent the headers.
            ex ("header-name", "header value")
        """

        # save the status and headers to use during finish_response
        self._response_status = status
        self._response_headers = [
            ("Server", "Adaruit_HTTPServer"),
            ("Connection", "close"),
        ] + headers

    def __finish_response(self, conn, result):
        """
        Called after the application callbile returns result data to respond with.
        Creates the HTTP Response payload from the response_headers and results data,
        and sends it back to client.

        :param string result: the data string to send back in the response to the client.
        """
        try:
            # First send the status and headers
            response = "HTTP/1.1 {0}\r\n".format(
                self._response_status or HTTPStatus.INTERNAL_SERVER_ERROR
            )
            for header in self._response_headers:
                response += "{0}: {1}\r\n".format(*header)
            response += "\r\n"
            if self._debug:
                print(f"Sending headers: {len(response)} bytes")
                # print(f"{response}")
            self.__send_bytes(conn, response.encode("utf-8"))

            # Next send the body
            for data in result:
                if self._debug:
                    print(f"Sending data: {len(data)} bytes")
                    # print(f"{data}")
                if isinstance(data, bytes):
                    self.__send_bytes(conn, data)
                else:
                    self.__send_bytes(conn, data.encode("utf-8"))
        finally:
            # Cleanup
            gc.collect()

    @staticmethod
    def __send_bytes(conn, buf):
        bytes_sent = 0
        bytes_to_send = len(buf)
        view = memoryview(buf)
        while bytes_sent < bytes_to_send:
            try:
                bytes_sent += conn.send(view[bytes_sent:])
            except OSError as exc:
                if exc.errno == EAGAIN:
                    continue
                if exc.errno == ECONNRESET:
                    return

    def __get_environ(self, request_text, remote_address) -> Dict[str, str]:
        """
        The environ dict containing the metadata about the incoming request and body
        Modeled after the WSGI environ dictionary and the PEP3333 standard.
        Follows the CGI/1.1 standard for Metadata.
        """
        env = {
            "GATEWAY_INTERFACE": "CGI/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "REMOTE_HOST": remote_address[0],
            "REMOTE_ADDR": remote_address[0],
        }

        try:
            # look for a double line ending to detect presense of a request body
            if "\n\n" in request_text:
                request_head, request_body = request_text.split("\n\n", 1)
            else:
                request_head = request_text
                request_body = ""

            # Process the request headers first by splitting them on \n
            header_lines = request_head.split("\n")
            # Split first line to get method, path, and HTTP version
            (method, path, httpversion) = header_lines[0].split()
            env["REQUEST_METHOD"] = method
            env["SERVER_PROTOCOL"] = httpversion
            env["SERVER_PORT"] = self._port
            env["SERVER_NAME"] = self._host
            # script name is the first path component
            env["SCRIPT_NAME"] = path.split("/", 1)[0]

            # split path and query string
            # TODO: This doesn't seem to match the CGI/1.1 spec.
            # See https://datatracker.ietf.org/doc/html/draft-coar-cgi-v11-03#section-4.1.5
            if path.find("?") >= 0:
                env["PATH_INFO"] = path.split("?")[0]
                env["QUERY_STRING"] = path.split("?")[1]
            else:
                env["PATH_INFO"] = path
                env["QUERY_STRING"] = ""

            # load the remaining header values into a dict so we can access them by key
            # since some metadata requires several of the header values
            headers = self.parse_headers(header_lines[1:])

            if "content-type" in headers:
                env["CONTENT_TYPE"] = headers.get("content-type")

            # truncate body to content length, it should already be this size but just in case.
            if "content-length" in headers:
                env["CONTENT_LENGTH"] = headers.get("content-length")
                env["wsgi.input"] = io.StringIO(
                    request_body[: int(env["CONTENT_LENGTH"])]
                )
            else:
                env["wsgi.input"] = io.StringIO(request_body)

            # place the all of headers into the environ dict using
            # HTTP_ prefix to match the CGI standard
            for name, value in headers.items():
                key = "HTTP_" + name.replace("-", "_").upper()
                if key in env:
                    value = "{0},{1}".format(env[key], value)
                env[key] = value

        except ValueError as exc:
            raise ValueError("Unparseable raw_request: ", request_text) from exc

        return env

    # # Utility functions
    @staticmethod
    def parse_headers(header_lines):
        """
        Parses the header portion of an HTTP request from the socket.
        Expects first line of HTTP request to have been read already.
        """
        headers = {}
        for header_line in header_lines:
            if header_line == "":
                break
            title, content = header_line.split(":", 1)
            headers[title.strip().lower()] = content.strip()
        return headers
