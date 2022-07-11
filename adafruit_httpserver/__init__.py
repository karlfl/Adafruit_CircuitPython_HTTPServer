# SPDX-FileCopyrightText: Copyright (c) 2022 Karl Fleischmann
# SPDX-License-Identifier: MIT
"""
================================================================================
`WebServer`
Simple Web (http) Server for CircuitPython that implements the PEP3333 standard

* Author(s): Karl Fleischmann

Implementation Notes
--------------------

Adapted from
    https://github.com/adafruit/Adafruit_CircuitPython_HTTPServer
    https://github.com/adafruit/Adafruit_CircuitPython_WSGI

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
"""

from adafruit_httpserver.httpstatus import HTTPStatus
from adafruit_httpserver.mimetype import MIMEType
from adafruit_httpserver.httpserver import HTTPServer
from adafruit_httpserver.httprequest import _HTTPRequest
from adafruit_httpserver.httpresponse import HTTPResponse
