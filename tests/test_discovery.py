#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the UDP autodiscovery functionality.
This script simulates both the CoreHub broadcast and the client discovery.
"""

import asyncio
import logging
import socket
import sys
import time
import pytest
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("discovery-test")

# Constants
DISCOVERY_MESSAGE = b"GLUESYNC BROADCAST MESSAGE"
START_PORT = 1717
PORT_RANGE = 10
BROADCAST_INTERVAL = 1.0  # seconds


def simulate_corehub_broadcast():
    """
    Simulates a CoreHub broadcasting discovery messages.
    """
    logger.info("Starting simulated CoreHub broadcast")
    
    # Create a UDP socket for broadcasting
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try:
        while True:
            # Broadcast to all ports in the range
            for port in range(START_PORT + 1, START_PORT + PORT_RANGE + 1):
                logger.debug(f"Broadcasting to port {port}")
                sock.sendto(DISCOVERY_MESSAGE, ("255.255.255.255", port))
                time.sleep(0.1)  # Small delay between broadcasts
            
            time.sleep(BROADCAST_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Stopping broadcast")
    finally:
        sock.close()


@pytest.mark.asyncio
async def test_discovery():
    """
    Test the discovery functionality by importing and using the CoreHubDiscovery class.
    """
    try:
        # Import the discovery module
        from gluesync_sdk.discovery import CoreHubDiscovery, get_corehub_address
        
        logger.info("Testing CoreHubDiscovery class...")
        discovery = CoreHubDiscovery(start_port=START_PORT, port_range=PORT_RANGE)
        
        try:
            # Try to discover the CoreHub
            logger.info("Attempting to discover CoreHub...")
            corehub_address = await discovery.discover_corehub()
            logger.info(f"SUCCESS! CoreHub discovered at {corehub_address}")
            
            # Test the convenience function
            logger.info("Testing get_corehub_address function...")
            address = await get_corehub_address(start_port=START_PORT, port_range=PORT_RANGE)
            logger.info(f"SUCCESS! get_corehub_address returned {address}")
            
            return True
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import discovery module: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


async def main():
    """
    Main entry point for the test script.
    """
    # Start the simulated CoreHub broadcast in a separate thread
    broadcast_thread = Thread(target=simulate_corehub_broadcast)
    broadcast_thread.daemon = True
    broadcast_thread.start()
    
    # Give the broadcast a moment to start
    await asyncio.sleep(1)
    
    # Test the discovery
    success = await test_discovery()
    
    # Wait for user to terminate
    if success:
        logger.info("Test completed successfully! Press Ctrl+C to exit.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        logger.error("Test failed.")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
        sys.exit(0)
