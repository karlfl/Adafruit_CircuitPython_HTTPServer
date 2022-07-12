# SPDX-FileCopyrightText: Copyright (c) 2022 Karl Fleischmann
# SPDX-License-Identifier: MIT
"""
`adafruit_httpserver.httprequest`
====================================================
Circuit Python HTTP Server HTTP Response class.

* Author(s): Karl Fleischmann
"""
try:
    from typing import Optional
except ImportError:
    pass


from adafruit_httpserver.httpstatus import HTTPStatus
from adafruit_httpserver.mimetype import MIMEType


class HTTPResponse:
    """Details of an HTTP response. Use in @`HTTPServer.route` decorator functions."""

    def __init__(
        self,
        *,
        status: tuple = HTTPStatus.OK,
        content_type: str = MIMEType.TEXT_PLAIN,
        body: str = "",
        filename: Optional[str] = None,
        root: str = "",
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """Create an HTTP response.

        :param tuple status: The HTTP status code to return, as a tuple of (int, "message").
          Common statuses are available in `HTTPStatus`.
        :param str content_type: The MIME type of the data being returned.
          Common MIME types are available in `MIMEType`.
        :param list headers (): a list of tuples to represent the headers.
            ex [("header-name", "header value"),("header-name", "header value")]
        :param Union[str|bytes] body:
          The data to return in the response body, if ``filename`` is not ``None``.
        :param str filename: If not ``None``,
          return the contents of the specified file, and ignore ``body``.
        :param str root: root directory for filename, without a trailing slash
        """
        self._status = status
        self._content_type = (
            content_type if not filename else MIMEType.mime_type(filename)
        )
        self._headers = headers or []
        self._body = body
        # ensure path contains trailing slash
        self._root = root.rstrip("/") + "/"
        # ensure filename doesn't start with slash
        self._filename = filename.lstrip("/") if filename else None
        self._filepath = self._root + self._filename if self._filename else None
        self._body = body.encode() if isinstance(body, str) else body
        self._root = root

        # if this is a file, load the body with it's contents
        if self._filepath is not None:
            try:
                with open(self._filepath, "rb") as file:
                    self._body = file.read()
            except OSError:
                self._status = HTTPStatus.NOT_FOUND
                self._content_type = (MIMEType.TEXT_PLAIN,)
                self._body = f"{HTTPStatus.NOT_FOUND} {self._filepath}\r\n"

    @property
    def status(self) -> str:
        """
        the HTTP Headers for this response
        """
        return self._status

    @property
    def headers(self) -> dict[str, str]:
        """
        the HTTP Headers for this response
        """
        headers = [
            ("Content-Type", self._content_type),
            ("Content-Length", str(len(self._body))),
        ] + self._headers
        return headers

    @property
    def body(self) -> bytes:
        """
        the HTTP Body for this response
        """
        return self._body

    @property
    def filename(self):
        """
        the file to be used for this response
        """
        return self._filename

    @property
    def rootfolder(self):
        """
        the file to be used for this response
        """
        return self._root
