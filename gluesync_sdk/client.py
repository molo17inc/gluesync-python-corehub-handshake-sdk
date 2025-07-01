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
from .discovery import get_corehub_address, CoreHubDiscovery
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
        host: Optional[str] = None,
        port: int = 1717,
        license_file_path: str = "gs-license.dat",
        module_tag: str = "python-module",
        use_ssl: bool = False,
        keystore_path: Optional[str] = None,
        keystore_password: Optional[str] = None,
        security_config: Optional[str] = None,
        ping_interval: float = 1.0,
        timeout: float = 10.0,
        discovery_start_port: int = 1717,
        discovery_port_range: int = 10,
        verify_ssl: bool = True
    ):
        """
        Initialize the Gluesync client.
        
        Args:
            host: Hostname or IP address of the CoreHub
            port: Port number for the CoreHub WebSocket
            license_file_path: Path to the gs-license.dat file
            module_tag: Name/tag for this module
            use_ssl: Whether to use SSL/TLS for the connection
            keystore_path: Path to the JKS keystore file (can be overridden by security_config)
            keystore_password: Password for the JKS keystore (can be overridden by security_config)
            security_config: Path to the security configuration JSON file (contains SSL and DH parameters)
            ping_interval: Interval in seconds between ping messages
            timeout: Connection timeout in seconds
            discovery_start_port: Starting port for CoreHub discovery
            discovery_port_range: Number of ports to scan during discovery
            verify_ssl: Whether to verify the SSL certificate
            
        Raises:
            GluesyncLicenseError: If the license file is invalid
            GluesyncSSLError: If SSL configuration is invalid
        """
        self.host = host
        self.port = port
        self.module_tag = module_tag
        self.use_ssl = use_ssl
        self.ping_interval = ping_interval
        self.timeout = timeout
        self.discovery_start_port = discovery_start_port
        self.discovery_port_range = discovery_port_range
        self.security_config = security_config
        self.verify_ssl = verify_ssl
        
        # Store license file path
        self.license_file_path = license_file_path
        self._license_content = None
            
        # SSL context setup
        self.ssl_context = None
        if self.use_ssl:
            try:
                # Create an SSL context that skips certificate verification if verify_ssl is False
                self.ssl_context = ssl.create_default_context()
                self.ssl_context.check_hostname = self.verify_ssl
                self.ssl_context.verify_mode = ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE
                
                # If security_config is provided, use it for SSL configuration
                if security_config:
                    import json
                    import os
                    
                    # Log the absolute path to the security config file
                    abs_security_config = os.path.abspath(security_config)
                    logger.info(f"Loading security config from: {abs_security_config}")
                    
                    if not os.path.exists(abs_security_config):
                        raise GluesyncSSLError(f"Security config file not found: {abs_security_config}")
                    
                    with open(abs_security_config, 'r') as f:
                        config = json.load(f)
                        # logger.info(f"Loaded security config: {config}")
                    
                    if 'ssl' not in config:
                        raise GluesyncSSLError(f"SSL configuration not found in security config file")
                    
                    ssl_config = config['ssl']
                    
                    # Use the SSL config from the file
                    jks_path = ssl_config.get('sslCertificatePath')
                    cert_password = ssl_config.get('certificatePassword')
                    
                    # Make sure the certificate path is absolute
                    if jks_path and not os.path.isabs(jks_path):
                        # If path is relative, resolve it relative to the config file location
                        config_dir = os.path.dirname(os.path.abspath(security_config))
                        jks_path = os.path.join(config_dir, jks_path)
                        logger.info(f"Resolved relative certificate path to: {jks_path}")
                    
                    # Log the certificate path
                    logger.info(f"Using certificate path: {jks_path}")
                    
                    if not jks_path or not cert_password:
                        raise GluesyncSSLError("SSL certificate path and password are required in security config")
                    
                    # Verify certificate file exists
                    if not os.path.exists(jks_path):
                        raise GluesyncSSLError(f"Certificate file not found at path: {jks_path}")
                        
                    try:
                        # Create SSL context with the config from the file
                        self.ssl_context = create_ssl_context_from_jks(
                            jks_path, 
                            cert_password,
                            alias=ssl_config.get('certificateAlias'),
                            key_password=ssl_config.get('certificateKeyPassword')
                        )
                        logger.info("SSL context created successfully from security config")
                    except Exception as e:
                        logger.error(f"Failed to create SSL context from {jks_path}: {str(e)}")
                        raise GluesyncSSLError(f"Failed to create SSL context: {str(e)}")
                else:
                    # Fall back to direct parameters if security_config is not provided
                    if not keystore_path or not keystore_password:
                        raise GluesyncSSLError("Keystore path and password are required for SSL connections")
                    
                    # Verify certificate file exists
                    if not os.path.exists(keystore_path):
                        raise GluesyncSSLError(f"Certificate file not found at path: {keystore_path}")
                        
                    try:
                        self.ssl_context = create_ssl_context_from_jks(keystore_path, keystore_password)
                        logger.info("SSL context created successfully")
                    except Exception as e:
                        logger.error(f"Failed to create SSL context from {keystore_path}: {str(e)}")
                        raise GluesyncSSLError(f"Failed to create SSL context: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to create SSL context: {e}")
                raise GluesyncSSLError(f"Failed to create SSL context: {e}")
        
        # Setup WebSocket connection
        self._connection = None
        self._token = None
        self._reconnecting = False
        self._reconnect_task = None
        
        # Event handlers
        self.on_connected: Optional[Callable[[str], Any]] = None
        self.on_disconnected: Optional[Callable[[str], Any]] = None
        self.on_error: Optional[Callable[[Exception], Any]] = None
        self.on_reconnecting: Optional[Callable[[], Any]] = None
        self.on_reconnected: Optional[Callable[[str], Any]] = None
        self.on_token_updated: Optional[Callable[[str], Any]] = None
    
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
        
        If a host was not explicitly provided in __init__, this method will
        attempt to discover the CoreHub on the local network before connecting.
        
        Returns:
            The JWT token received from the server
            
        Raises:
            GluesyncConnectionError: If the connection fails
            GluesyncAuthenticationError: If authentication fails
        """
        if self.is_connected:
            logger.warning("Already connected to CoreHub")
            return self.token
        
        # Use autodiscovery if host is not provided
        host = self.host
        if host is None:
            try:
                logger.info("No host provided, using UDP autodiscovery to find CoreHub...")
                host = await get_corehub_address(
                    start_port=self.discovery_start_port,
                    port_range=self.discovery_port_range,
                    ssl_context=self.ssl_context,
                    verify_ssl=self.verify_ssl
                )
                # Save the discovered host to the instance
                self.host = host
                logger.info(f"CoreHub discovered at {host}")
            except Exception as e:
                logger.error(f"Failed to discover CoreHub: {e}")
                raise GluesyncConnectionError(f"Failed to discover CoreHub: {e}")
            
        # Create a new connection
        self._connection = WebSocketConnection(
            host=host,
            port=self.port,
            headers=self.get_connection_headers(),
            ssl_context=self.ssl_context,
            ping_interval=self.ping_interval,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl
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
            
        # Notify token update listeners when initially connected
        if self.on_token_updated:
            await self._call_callback(self.on_token_updated, token)
    
    async def _handle_disconnected(self, reason: str):
        """
        Handle the disconnected event.
        
        Args:
            reason: The reason for disconnection
        """
        logger.info(f"Disconnected from CoreHub: {reason}")
        
        if self.on_disconnected:
            await self._call_callback(self.on_disconnected, reason)
        
        # Start the reconnection process if not already reconnecting
        if not self._reconnecting:
            self._start_reconnect_task()
    
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
            
    def _start_reconnect_task(self):
        """
        Start the reconnection task if not already running.
        """
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect())
            
    async def _reconnect(self):
        """
        Reconnection logic. First tries to reconnect to the specified/known host.
        If that fails, attempts to re-discover the CoreHub in case its IP address has changed.
        """
        if self._reconnecting:
            return
            
        self._reconnecting = True
        logger.info("Starting reconnection process...")
        
        # Notify listeners that we're trying to reconnect
        if self.on_reconnecting:
            await self._call_callback(self.on_reconnecting)
        
        try:
            # If a specific host is provided, try to reconnect directly first
            if self.host:
                logger.info(f"CoreHub address known ({self.host}), attempting direct reconnection...")
                try:
                    await self._attempt_reconnect()
                    return  # Successfully reconnected, exit early
                except Exception as reconnect_error:
                    logger.warning(f"Direct reconnection to {self.host} failed: {reconnect_error}")
                    logger.info("CoreHub may have changed IP address, attempting re-discovery...")
                    
            # Either no host was provided initially or direct reconnection failed,
            # so attempt discovery
            try:
                # Clear the previous host so we truly re-discover
                previous_host = self.host
                self.host = None
                
                discovery = CoreHubDiscovery(start_port=self.discovery_start_port, port_range=self.discovery_port_range)
                corehub_address = await discovery.discover_corehub(ssl_context=self.ssl_context, verify_ssl=self.verify_ssl)
                
                # If discovered a new host different from previous one, log it
                if previous_host and previous_host != corehub_address:
                    logger.info(f"CoreHub IP changed from {previous_host} to {corehub_address}")
                    
                # Save the discovered host
                self.host = corehub_address
                logger.info(f"CoreHub discovered at {corehub_address}, attempting reconnection...")
                
                # Now attempt to reconnect with the discovered address
                await self._attempt_reconnect()
            except Exception as discovery_error:
                logger.error(f"Failed to discover CoreHub: {discovery_error}")
                # Restore the previous host in case we want to retry later
                if previous_host:
                    self.host = previous_host
                # Set reconnecting to false to allow future reconnection attempts
                self._reconnecting = False
        except Exception as e:
            logger.error(f"Error during reconnection: {e}")
            # Set reconnecting to false to allow future reconnection attempts
            self._reconnecting = False
            
    async def _attempt_reconnect(self):
        """
        Attempt to reconnect to the CoreHub.
        """
        try:
            # Create a new connection
            self._connection = WebSocketConnection(
                host=self.host,
                port=self.port,
                headers=self.get_connection_headers(),
                ssl_context=self.ssl_context,
                ping_interval=self.ping_interval,
                timeout=self.timeout,
                verify_ssl=self.verify_ssl
            )
            
            # Set up event handlers
            self._connection.on_connected = self._handle_connected
            self._connection.on_disconnected = self._handle_disconnected
            self._connection.on_error = self._handle_error
            
            # Connect to the server
            token = await self._connection.connect()
            self._token = token
            
            # Successfully reconnected
            logger.info(f"Successfully reconnected to CoreHub at {self.host}:{self.port}")
            self._reconnecting = False
            
            # Notify listeners that we've reconnected
            if self.on_reconnected:
                await self._call_callback(self.on_reconnected, token)
                
            # Always notify token update listeners when reconnected with a new token
            if self.on_token_updated:
                await self._call_callback(self.on_token_updated, token)
                
            return token
        except Exception as e:
            logger.error(f"Reconnection attempt failed: {e}")
            self._reconnecting = False
            raise
