#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gluesync Python SDK for CoreHub connection.

This SDK provides a client-side interface for interacting with the Gluesync CoreHub 
through a WebSocket connection. It implements the complete client-server handshake process 
and supports both WS and WSS connections using JKS certificates.

Gluesync SDK is dual-licensed under the following licenses:

1. GNU General Public License (GPL) Version 3
   You may use, modify, and distribute this software under the terms of the GPL v3.
   See the LICENSE-GPL file or <http://www.gnu.org/licenses/gpl-3.0.html> for details.
   This option is available at no cost, but any derivative works must also be licensed under GPL v3.

2. MOLO17 Commercial License
   Alternatively, you may use this software under the MOLO17 Commercial License,
   which includes a warranty and permits proprietary use. Contact MOLO17 at info@molo17.com
   for licensing terms and conditions.

You must choose one of these licenses to use this software. Using this software implies
acceptance of one of these licenses. See the accompanying LICENSE files or contact
MOLO17 for more information.

Copyright (C) 2025 MOLO17. All rights reserved.
"""

from importlib.metadata import PackageNotFoundError, version as _package_version

# The release version comes from the tag (CI writes it into setup.py at build
# time), so read it from the installed package instead of hardcoding it here.
try:
    __version__ = _package_version("gluesync-sdk")
except PackageNotFoundError:  # running from a source checkout, not installed
    __version__ = "0.0.0.dev0"
__author__ = "MOLO17"
__email__ = "info@molo17.com"

import logging

# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Export main components
from .client import GluesyncClient
from .exceptions import (
    GluesyncError,
    GluesyncConnectionError,
    GluesyncAuthenticationError,
    GluesyncLicenseError,
    GluesyncSSLError,
    GluesyncTimeoutError,
    GluesyncHandshakeError,
    GluesyncClosedError
)
from .utils import create_ssl_context_from_jks
from .discovery import get_corehub_address, CoreHubDiscovery

# Define public API
__all__ = [
    "GluesyncClient",
    "GluesyncError",
    "GluesyncConnectionError",
    "GluesyncAuthenticationError",
    "GluesyncLicenseError",
    "GluesyncSSLError",
    "GluesyncTimeoutError",
    "GluesyncHandshakeError",
    "GluesyncClosedError",
    "create_ssl_context_from_jks",
    "get_corehub_address",
    "CoreHubDiscovery"
]
