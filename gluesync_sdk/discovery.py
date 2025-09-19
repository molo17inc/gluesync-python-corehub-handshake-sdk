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
    
    async def discover_corehub(self, ssl_context=None, verify_ssl: bool = True) -> str:
        """
        Listen for the CoreHub broadcast message and return the CoreHub IP address.
        
        Args:
            ssl_context: SSL context to use for secure connections
            verify_ssl: Whether to verify SSL certificates (default: True)
        
        Returns:
            The IP address of the CoreHub as a string
            
        Raises:
            ConnectionError: If unable to bind to a socket or other network issues
            TimeoutError: If no broadcast is received within the timeout period
        """
        # Choose a random port from the range to listen on
        port = random.choice(self.port_list)
        
        # Create a UDP socket
        sock = None
        
        try:
            # Create and configure the socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Set socket timeout to prevent blocking forever
            sock.settimeout(5)
            
            # Try to bind to the chosen port
            try:
                sock.bind(("0.0.0.0", port))
                logger.debug(f"Listening for CoreHub broadcast on port {port}")
            except OSError as e:
                # Port might be in use, try with another port
                logger.debug(f"Port {port} already in use, trying another port...")
                sock.close()
                # Small delay before recursively trying again
                await asyncio.sleep(1)
                return await self.discover_corehub()
            
            # Wait for a broadcast message in a non-blocking way
            while True:
                try:
                    # This is a blocking call but has a timeout set
                    data, addr = sock.recvfrom(1024)
                    
                    logger.debug(f"Received data from {addr[0]}: {data}")
                    
                    # Check if this is the expected discovery message
                    if data == DISCOVERY_MESSAGE:
                        corehub_address = addr[0]
                        logger.info(f"CoreHub discovered at {corehub_address}")
                        return corehub_address
                    
                except socket.timeout:
                    # Continue listening after timeout
                    logger.debug("No broadcast received, continuing to listen...")
                    # We can use a sleep to prevent CPU spinning
                    await asyncio.sleep(0.1)
                    continue
                    
                except Exception as e:
                    logger.error(f"Error while listening for broadcast: {e}")
                    raise ConnectionError(f"Error while listening for broadcast: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to discover CoreHub: {e}")
            raise ConnectionError(f"Failed to discover CoreHub: {e}")
            
        finally:
            # Clean up the socket
            if sock:
                sock.close()


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
