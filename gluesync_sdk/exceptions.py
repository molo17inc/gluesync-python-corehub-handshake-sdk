#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This file is part of Gluesync Scheduler Module.

Gluesync Scheduler Module is dual-licensed under the following licenses:

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


class GluesyncError(Exception):
    """Base exception for Gluesync SDK."""
    pass


class GluesyncConnectionError(GluesyncError):
    """Exception raised for connection-related errors."""
    pass


class GluesyncAuthenticationError(GluesyncError):
    """Exception raised for authentication failures."""
    pass


class GluesyncLicenseError(GluesyncError):
    """Exception raised for license-related errors."""
    pass


class GluesyncTimeoutError(GluesyncConnectionError):
    """Exception raised when operations timeout."""
    pass


class GluesyncSSLError(GluesyncConnectionError):
    """Exception raised for SSL/TLS certificate issues."""
    pass


class GluesyncProtocolError(GluesyncError):
    """Exception raised for protocol-related errors."""
    pass


class GluesyncHandshakeError(GluesyncProtocolError):
    """Exception raised for handshake failures."""
    pass


class GluesyncClosedError(GluesyncConnectionError):
    """Exception raised when attempting to use a closed connection."""
    pass
