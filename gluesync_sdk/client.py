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

import asyncio
import logging
import os
import ssl
from typing import Optional, Dict, Callable, Any, Union

from .connection import WebSocketConnection
from .utils import create_ssl_context_from_jks
from .exceptions import (
    GluesyncError,
    GluesyncConnectionError,
    GluesyncAuthenticationError,
    GluesyncLicenseError,
    GluesyncSSLError
)


logger = logging.getLogger("Gluesync.client")


class GluesyncClient:
    """
    Main client for interacting with Gluesync CoreHub services.
    Manages the connection, authentication, and WebSocket communication with the CoreHub.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        license_file_path: str,
        module_tag: str,
        ssl: bool = False,
        keystore_path: Optional[str] = None,
        keystore_password: Optional[str] = None,
        ping_interval: float = 1.0,
        timeout: float = 10.0
    ):
        """
        Initialize the Gluesync client.
        
        Args:
            host: Hostname or IP address of the CoreHub
            port: Port number for the CoreHub WebSocket
            license_file_path: Path to the gs-license.dat file
            module_tag: Name/tag for this module
            ssl: Whether to use SSL/TLS for the connection
            keystore_path: Path to the JKS keystore file (required if ssl=True)
            keystore_password: Password for the JKS keystore (required if ssl=True)
            ping_interval: Interval in seconds between ping messages
            timeout: Connection timeout in seconds
            
        Raises:
            GluesyncLicenseError: If the license file is invalid
            GluesyncSSLError: If SSL configuration is invalid
        """
        self.host = host
        self.port = port
        self.module_tag = module_tag
        self.use_ssl = ssl
        self.ping_interval = ping_interval
        self.timeout = timeout
        
        # Store license file path
        self.license_file_path = license_file_path
        self._license_content = None
            
        # SSL context setup
        self.ssl_context = None
        if self.use_ssl:
            if not keystore_path or not keystore_password:
                raise GluesyncSSLError("Keystore path and password are required for SSL connections")
                
            try:
                self.ssl_context = create_ssl_context_from_jks(keystore_path, keystore_password)
                logger.info("SSL context created successfully")
            except Exception as e:
                logger.error(f"Failed to create SSL context: {e}")
                raise GluesyncSSLError(f"Failed to create SSL context: {e}")
        
        # Setup WebSocket connection
        self._connection = None
        self._token = None
        
        # Event handlers
        self.on_connected: Optional[Callable[[str], Any]] = None
        self.on_disconnected: Optional[Callable[[str], Any]] = None
        self.on_error: Optional[Callable[[Exception], Any]] = None
    
    @property
    def token(self) -> Optional[str]:
        """
        Get the JWT token received from CoreHub after authentication.
        
        Returns:
            The JWT token as a string, or None if not authenticated
        """
        if self._connection and self._connection.token:
            return self._connection.token
        return self._token
    
    @property
    def connection_status(self) -> str:
        """
        Get the current connection status.
        
        Returns:
            String describing the connection status
        """
        if not self._connection:
            return "Not initialized"
            
        if self._connection.is_connected:
            return "Connected"
            
        return "Disconnected"
    
    @property
    def is_connected(self) -> bool:
        """
        Check if the client is currently connected to CoreHub.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connection is not None and self._connection.is_connected
    
    def get_connection_headers(self) -> Dict[str, str]:
        """
        Generate the HTTP headers for the WebSocket connection.
        
        Returns:
            Dictionary of HTTP headers
            
        Raises:
            GluesyncLicenseError: If the license file cannot be read
        """
        headers = {
            "Module-License": self._get_license_content(),
            "Module-Tag": self.module_tag
        }
        return headers
        
    def _get_license_content(self) -> str:
        """
        Load and get the license content from the file.
        
        Returns:
            The license content as a string
            
        Raises:
            GluesyncLicenseError: If the license file cannot be read
        """
        if self._license_content is None:
            if not os.path.exists(self.license_file_path):
                raise GluesyncLicenseError(f"License file not found: {self.license_file_path}")
                
            try:
                with open(self.license_file_path, 'r') as file:
                    self._license_content = file.read().strip()
            except Exception as e:
                raise GluesyncLicenseError(f"Failed to read license file: {e}")
                
        return self._license_content
    
    async def connect(self) -> str:
        """
        Connect to the CoreHub and perform the handshake authentication.
        
        Returns:
            The JWT token received from the server
            
        Raises:
            GluesyncConnectionError: If the connection fails
            GluesyncAuthenticationError: If authentication fails
        """
        if self.is_connected:
            logger.warning("Already connected to CoreHub")
            return self.token
            
        # Create a new connection
        self._connection = WebSocketConnection(
            host=self.host,
            port=self.port,
            headers=self.get_connection_headers(),
            ssl_context=self.ssl_context,
            ping_interval=self.ping_interval,
            timeout=self.timeout
        )
        
        # Set up event handlers
        self._connection.on_connected = self._handle_connected
        self._connection.on_disconnected = self._handle_disconnected
        self._connection.on_error = self._handle_error
        
        # Connect to the server
        token = await self._connection.connect()
        self._token = token
        return token
    
    async def disconnect(self):
        """
        Disconnect from the CoreHub.
        
        Raises:
            GluesyncConnectionError: If an error occurs during disconnection
        """
        if not self.is_connected:
            logger.warning("Not connected to CoreHub")
            return
            
        await self._connection.disconnect()
    
    async def _handle_connected(self, token: str):
        """
        Handle the connected event.
        
        Args:
            token: The JWT token received from the server
        """
        logger.info("Connected to CoreHub successfully")
        self._token = token
        
        if self.on_connected:
            await self._call_callback(self.on_connected, token)
    
    async def _handle_disconnected(self, reason: str):
        """
        Handle the disconnected event.
        
        Args:
            reason: The reason for disconnection
        """
        logger.info(f"Disconnected from CoreHub: {reason}")
        
        if self.on_disconnected:
            await self._call_callback(self.on_disconnected, reason)
    
    async def _handle_error(self, error: Exception):
        """
        Handle the error event.
        
        Args:
            error: The exception that occurred
        """
        logger.error(f"Error in connection: {error}")
        
        if self.on_error:
            await self._call_callback(self.on_error, error)
    
    async def _call_callback(self, callback: Callable, *args, **kwargs):
        """
        Call a callback function safely, handling any exceptions.
        
        Args:
            callback: The callback function to call
            *args: Positional arguments to pass to the callback
            **kwargs: Keyword arguments to pass to the callback
        """
        try:
            result = callback(*args, **kwargs)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Error in callback: {e}")
