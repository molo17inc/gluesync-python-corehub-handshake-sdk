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

import os
import ssl
import jks
import tempfile
from typing import Optional, Tuple


def create_ssl_context_from_jks(keystore_path: str, keystore_password: str, alias: str = None, key_password: str = None) -> ssl.SSLContext:
    """
    Create an SSL context from a Java KeyStore (JKS) file.
    
    Args:
        keystore_path: Path to the JKS file
        keystore_password: Password for the JKS file
        alias: Optional alias for the certificate in the keystore
        key_password: Optional password for the certificate key
        
    Returns:
        SSL context configured with the certificates from the JKS file
    """
    # Create a default SSL context
    context = ssl.create_default_context()
    
    # Load the JKS keystore
    ks = jks.KeyStore.load(keystore_path, keystore_password)
    
    # Get all certificates from the keystore
    with tempfile.NamedTemporaryFile(delete=False) as ca_cert_file:
        # If alias is specified, only extract that certificate
        if alias and alias in ks.certs:
            cert = ks.certs[alias]
            ca_cert_file.write(cert.cert)
        else:
            # Otherwise extract all certificates
            for cert_alias, cert in ks.certs.items():
                ca_cert_file.write(cert.cert)
    
    # Load certificates to the SSL context
    context.load_verify_locations(cafile=ca_cert_file.name)
    
    # Clean up temporary file
    os.unlink(ca_cert_file.name)
    
    # Configure SSL settings
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    
    return context


def parse_close_reason(reason: str) -> Tuple[str, str]:
    """
    Parse a WebSocket close reason into error code and message.
    
    Args:
        reason: The close reason string from the WebSocket
        
    Returns:
        Tuple of (error_code, error_message)
    """
    if ":" in reason:
        parts = reason.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return "UNKNOWN", reason


def get_error_from_close_reason(reason: str) -> Optional[str]:
    """
    Extract a user-friendly error message from a close reason.
    
    Args:
        reason: The close reason string from the WebSocket
        
    Returns:
        An error message suitable for display to the user
    """
    error_code, error_message = parse_close_reason(reason)
    
    error_messages = {
        "NOT_CONSISTENT": "Authentication failed: Invalid headers or license information",
        "VIOLATED_POLICY": "License not valid or expired",
        "INTERNAL_ERROR": "Server error: Please check CoreHub logs for more information",
        "CLOSED_ABNORMALLY": "Connection closed unexpectedly"
    }
    
    return error_messages.get(error_code, error_message)
