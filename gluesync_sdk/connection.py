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
import ssl
from typing import Optional, Callable, Dict, Any, Union
import websockets

# Handle different versions of websockets library
try:
    # For newer versions
    from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
    
    # Create a compatible ConnectionClosed class
    class ConnectionClosed(Exception):
        def __init__(self, reason=""):
            self.reason = reason
            super().__init__(reason)
            
    # Map the new exceptions to our compatible class
    websockets_connection_closed_exceptions = (ConnectionClosedOK, ConnectionClosedError)
except ImportError:
    # For older versions
    from websockets.exceptions import ConnectionClosed
    websockets_connection_closed_exceptions = (ConnectionClosed,)

from .exceptions import (
    GluesyncConnectionError,
    GluesyncAuthenticationError,
    GluesyncTimeoutError,
    GluesyncHandshakeError,
    GluesyncClosedError
)
from .utils import get_error_from_close_reason


logger = logging.getLogger("Gluesync.connection")


class WebSocketConnection:
    """
    Manages WebSocket connection to Gluesync CoreHub.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        headers: Dict[str, str],
        ssl_context: Optional[ssl.SSLContext] = None,
        ping_interval: float = 1.0,
        timeout: float = 10.0
    ):
        """
        Initialize the WebSocket connection.
        
        Args:
            host: Hostname or IP address of the CoreHub
            port: Port number
            headers: HTTP headers to send with the WebSocket handshake
            ssl_context: SSL context for secure connections (optional)
            ping_interval: Interval in seconds between ping messages
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.headers = headers
        self.ssl_context = ssl_context
        self.ping_interval = ping_interval
        self.timeout = timeout
        
        self.ws = None
        self.token = None
        self._ping_task = None
        self._receive_task = None
        self._connected = False
        
        # Event handlers
        self.on_connected: Optional[Callable[[str], Any]] = None
        self.on_disconnected: Optional[Callable[[str], Any]] = None
        self.on_error: Optional[Callable[[Exception], Any]] = None
    
    @property
    def is_connected(self) -> bool:
        """
        Check if the connection is established.
        
        Returns:
            True if connected, False otherwise
        """
        # Different versions of websockets library use different attributes
        # to check if the connection is closed
        if self._connected and self.ws is not None:
            try:
                # Try the closed attribute first (older versions)
                return not self.ws.closed
            except AttributeError:
                # For newer versions, check if the connection is open
                try:
                    return not self.ws.is_closing()
                except AttributeError:
                    # As a fallback, assume it's still connected if we have a ws object
                    return True
        return False
    
    @property
    def connection_url(self) -> str:
        """
        Get the WebSocket connection URL.
        
        Returns:
            The WebSocket URL as a string
        """
        protocol = "wss" if self.ssl_context else "ws"
        return f"{protocol}://{self.host}:{self.port}/ext-module"
    
    async def connect(self) -> str:
        """
        Establish a WebSocket connection to the CoreHub.
        
        Returns:
            The authentication token received from the server
            
        Raises:
            GluesyncConnectionError: If the connection fails
            GluesyncAuthenticationError: If authentication fails
            GluesyncTimeoutError: If the connection times out
        """
        try:
            # Connect to the WebSocket server
            try:
                # Try with additional_headers (websockets >= 11.0)
                self.ws = await asyncio.wait_for(
                    websockets.connect(
                        self.connection_url,
                        additional_headers=self.headers,
                        ssl=self.ssl_context
                    ),
                    timeout=self.timeout
                )
            except TypeError:
                try:
                    # Try with extra_headers (websockets >= 10.0, < 11.0)
                    self.ws = await asyncio.wait_for(
                        websockets.connect(
                            self.connection_url,
                            extra_headers=self.headers,
                            ssl=self.ssl_context
                        ),
                        timeout=self.timeout
                    )
                except TypeError:
                    # Fallback for older versions (no headers support)
                    logger.warning("Websockets version does not support headers, connecting without them")
                    self.ws = await asyncio.wait_for(
                        websockets.connect(
                            self.connection_url,
                            ssl=self.ssl_context
                        ),
                        timeout=self.timeout
                    )
            logger.info(f"Connected to {self.connection_url}")
            
            # Start the handshake by sending "hello"
            await self.ws.send("hello")
            logger.debug("Sent 'hello' message to CoreHub")
            
            # Wait for the token response
            response = await asyncio.wait_for(
                self.ws.recv(),
                timeout=self.timeout
            )
            
            # Check if the response is "pong" (should not happen at this stage)
            if response == "pong":
                raise GluesyncHandshakeError("Unexpected 'pong' message during handshake")
                
            # Store the token
            self.token = response
            self._connected = True
            logger.info("Authentication successful, received token")
            
            # Start the ping and receive tasks
            self._start_ping_task()
            self._start_receive_task()
            
            # Call the connected callback if set
            if self.on_connected:
                await self._call_callback(self.on_connected, self.token)
            
            return self.token
            
        except asyncio.TimeoutError:
            logger.error(f"Connection to {self.connection_url} timed out")
            raise GluesyncTimeoutError(f"Connection to {self.host}:{self.port} timed out")
            
        except ConnectionClosed as e:
            error_message = get_error_from_close_reason(str(e.reason))
            logger.error(f"Connection closed during handshake: {error_message}")
            raise GluesyncAuthenticationError(error_message)
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.connection_url}: {e}")
            if self.on_error:
                await self._call_callback(self.on_error, e)
            raise GluesyncConnectionError(f"Failed to connect: {e}")
    
    async def disconnect(self):
        """
        Disconnect from the CoreHub.
        
        Raises:
            GluesyncConnectionError: If an error occurs during disconnection
        """
        if not self.is_connected:
            return
            
        try:
            # Cancel the ping and receive tasks
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()
                
            if self._receive_task and not self._receive_task.done():
                self._receive_task.cancel()
            
            # Close the WebSocket connection
            await self.ws.close()
            self._connected = False
            self.token = None
            
            logger.info("Disconnected from CoreHub")
            
            # Call the disconnected callback if set
            if self.on_disconnected:
                await self._call_callback(self.on_disconnected, "Disconnected by client")
                
        except Exception as e:
            logger.error(f"Error during disconnection: {e}")
            if self.on_error:
                await self._call_callback(self.on_error, e)
            raise GluesyncConnectionError(f"Error during disconnection: {e}")
    
    def _start_ping_task(self):
        """
        Start the ping task to keep the connection alive.
        """
        if self._ping_task is None or self._ping_task.done():
            self._ping_task = asyncio.create_task(self._ping_loop())
    
    def _start_receive_task(self):
        """
        Start the receive task to handle incoming messages.
        """
        if self._receive_task is None or self._receive_task.done():
            self._receive_task = asyncio.create_task(self._receive_loop())
    
    async def _ping_loop(self):
        """
        Send ping messages at regular intervals to keep the connection alive.
        """
        try:
            while self.is_connected:
                await asyncio.sleep(self.ping_interval)
                if self.is_connected:
                    await self.ws.send("ping")
                    logger.debug("Sent 'ping' to CoreHub")
        except asyncio.CancelledError:
            logger.debug("Ping task cancelled")
        except Exception as e:
            logger.error(f"Error in ping loop: {e}")
            if self.on_error:
                await self._call_callback(self.on_error, e)
    
    async def _receive_loop(self):
        """
        Handle incoming messages from the CoreHub.
        """
        try:
            while self.is_connected:
                message = await self.ws.recv()
                logger.debug(f"Received message from CoreHub: {message}")
                
                # Handle pong messages
                if message == "pong":
                    logger.debug("Received 'pong' from CoreHub")
                else:
                    logger.warning(f"Received unexpected message: {message}")
        except asyncio.CancelledError:
            logger.debug("Receive task cancelled")
        except websockets_connection_closed_exceptions as e:
            self._connected = False
            # Handle different exception formats
            try:
                error_message = get_error_from_close_reason(str(e.reason))
            except AttributeError:
                error_message = str(e)
            logger.error(f"Connection closed: {error_message}")
            
            if self.on_disconnected:
                await self._call_callback(self.on_disconnected, error_message)
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            if self.on_error:
                await self._call_callback(self.on_error, e)
    
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
