#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This file is part of Gluesync.

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

import asyncio
import logging
import random
import socket
from typing import Optional, List, Tuple, Union
import os

logger = logging.getLogger("Gluesync.discovery")

# Constants for discovery
DISCOVERY_MESSAGE = b"GLUESYNC BROADCAST MESSAGE"
DEFAULT_START_PORT = 1717
DEFAULT_PORT_RANGE = 10  # Will scan ports from START_PORT+1 to START_PORT+DEFAULT_PORT_RANGE


class DiscoveryProtocol(asyncio.DatagramProtocol):
    """
    Native asyncio datagram protocol for non-blocking UDP discovery.
    """
    def __init__(self, target_message: bytes, future: asyncio.Future):
        self.target_message = target_message
        self.future = future
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if data == self.target_message:
            if not self.future.done():
                self.future.set_result(addr[0])

    def error_received(self, exc):
        if not self.future.done():
            self.future.set_exception(exc)


class CoreHubDiscovery:
    """
    Provides UDP autodiscovery for CoreHub servers on the local network.
    """
    
    def __init__(self, start_port: int = DEFAULT_START_PORT, port_range: int = DEFAULT_PORT_RANGE):
        """
        Initialize the CoreHub discovery service.
        
        Args:
            start_port: The base port number to use for discovery
            port_range: The number of ports to scan (starting from start_port + 1)
        """
        self.start_port = start_port
        self.port_range = port_range
        self.port_list = list(range(start_port + 1, start_port + port_range + 1))
    
    async def discover_corehub(self, ssl_context=None, verify_ssl: bool = True, timeout: float = 15.0) -> str:
        """
        Listen for the CoreHub broadcast message and return the CoreHub IP address.
        
        Args:
            ssl_context: SSL context to use for secure connections
            verify_ssl: Whether to verify SSL certificates (default: True)
            timeout: Timeout in seconds to wait for discovery (default: 15.0)
        
        Returns:
            The IP address of the CoreHub as a string
            
        Raises:
            ConnectionError: If unable to bind to a socket or other network issues
            TimeoutError: If no broadcast is received within the timeout period
        """
        # Choose a random port from the range to listen on
        port = random.choice(self.port_list)
        
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        
        try:
            # Create the datagram endpoint
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: DiscoveryProtocol(DISCOVERY_MESSAGE, future),
                local_addr=("0.0.0.0", port)
            )
            logger.debug(f"Listening for CoreHub broadcast on UDP port {port}")
        except OSError as e:
            # Port might be in use, try with another port
            logger.debug(f"Port {port} already in use: {e}. Trying another port...")
            # Small delay before recursively trying again
            await asyncio.sleep(1)
            return await self.discover_corehub(ssl_context, verify_ssl, timeout)
            
        try:
            # Wait for the future with a timeout
            corehub_address = await asyncio.wait_for(future, timeout=timeout)
            logger.info(f"CoreHub discovered at {corehub_address}")
            return corehub_address
        except asyncio.TimeoutError:
            logger.warning(f"Discovery timed out after {timeout} seconds")
            raise TimeoutError(f"Discovery timed out after {timeout} seconds")
        finally:
            transport.close()


async def get_corehub_address(env_var_name: str = "CORE_HUB_ADDRESS", 
                            start_port: int = DEFAULT_START_PORT,
                            port_range: int = DEFAULT_PORT_RANGE,
                            ssl_context = None,
                            verify_ssl: bool = True) -> str:
    """
    Get the CoreHub address from environment variable or via autodiscovery.
    
    Args:
        env_var_name: Name of the environment variable that might contain the CoreHub address
        start_port: The base port number to use for discovery
        port_range: The number of ports to scan (starting from start_port + 1)
        ssl_context: SSL context to use for secure connections
        verify_ssl: Whether to verify SSL certificates (default: True)
        
    Returns:
        The IP address of the CoreHub as a string
        
    Raises:
        ConnectionError: If unable to discover the CoreHub
    """
    # First check if the address is provided via environment variable
    core_hub_address = os.environ.get(env_var_name)
    
    if core_hub_address:
        logger.info(f"Using CoreHub address from environment: {core_hub_address}")
        return core_hub_address
    
    # If not provided, try to discover it on the network
    logger.info("CoreHub address not provided, attempting autodiscovery...")
    try:
        discovery = CoreHubDiscovery(start_port=start_port, port_range=port_range)
        return await discovery.discover_corehub(ssl_context=ssl_context, verify_ssl=verify_ssl)
    except Exception as e:
        logger.error(f"Failed to discover CoreHub: {e}")
        raise ConnectionError(f"Failed to discover CoreHub. Please provide the CoreHub address via the {env_var_name} environment variable.")
