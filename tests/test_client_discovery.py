#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the GluesyncClient with UDP autodiscovery.
This script simulates both the CoreHub broadcast and tests the client's autodiscovery.
"""

import asyncio
import socket
import threading
import time
import logging
import sys
import os
import pytest

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("client-discovery-test")

# Constants
DISCOVERY_MESSAGE = b"GLUESYNC BROADCAST MESSAGE"
START_PORT = 1717
PORT_RANGE = 10
BROADCAST_INTERVAL = 1.0  # seconds

# Flag to control the broadcast thread
running = True

# Check if running in CI environment
IN_CI = os.environ.get('CI', 'false').lower() == 'true'

def simulate_corehub_broadcast():
    """
    Simulates a CoreHub broadcasting discovery messages.
    """
    logger.info("Starting simulated CoreHub broadcast")
    
    # Create a UDP socket for broadcasting
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try:
        while running:
            # Broadcast to all ports in the range
            for port in range(START_PORT + 1, START_PORT + PORT_RANGE + 1):
                logger.debug(f"Broadcasting to port {port}")
                sock.sendto(DISCOVERY_MESSAGE, ("255.255.255.255", port))
                time.sleep(0.1)  # Small delay between broadcasts
            
            time.sleep(BROADCAST_INTERVAL)
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
    finally:
        sock.close()
        logger.info("Broadcast stopped")

@pytest.mark.asyncio
async def test_client_autodiscovery():
    """
    Test the GluesyncClient with autodiscovery.
    """
    global running
    try:
        # Start the simulated CoreHub broadcast in a separate thread
        broadcast_thread = threading.Thread(target=simulate_corehub_broadcast)
        broadcast_thread.daemon = True
        broadcast_thread.start()
        
        # Give the broadcast a moment to start
        await asyncio.sleep(1)
        
        from gluesync_sdk import GluesyncClient
        
        logger.info("Creating GluesyncClient with autodiscovery...")
        
        # Create a client without specifying the host to use autodiscovery
        client = GluesyncClient(
            host=None,  # None triggers autodiscovery
            port=START_PORT,
            license_file_path="dummy-license.dat",  # This is just for testing, won't be used
            module_tag="test-module",
            ssl=False,
            discovery_start_port=START_PORT,
            discovery_port_range=PORT_RANGE
        )
        
        # The host is discovered during connect(), not during initialization
        logger.info("Initial client host: None (expected)")
        
        try:
            # Try to connect - this should trigger autodiscovery
            logger.info("Calling connect() to trigger autodiscovery...")
            # We'll catch the connection error since we don't have a real CoreHub
            try:
                await client.connect()
            except Exception as e:
                # We expect this to fail with a connection error after discovery
                logger.info(f"Expected connection error after discovery: {e}")
            
            # Check if the host was discovered
            logger.info(f"Client host after connect attempt: {client.host}")
            
            if client.host:
                logger.info("SUCCESS! Client autodiscovery worked correctly.")
                success = True
            else:
                logger.error("Client autodiscovery failed to set the host.")
                success = False
                
            # Clean up
            running = False
            broadcast_thread.join(timeout=2)
            return success
        except Exception as e:
            logger.error(f"Error during connect/autodiscovery: {e}")
            running = False
            broadcast_thread.join(timeout=2)
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import GluesyncClient: {e}")
        return False
    except Exception as e:
        logger.error(f"Error testing client autodiscovery: {e}")
        running = False
        if 'broadcast_thread' in locals():
            broadcast_thread.join(timeout=2)
        return False

async def main():
    """
    Main entry point for the test script.
    """
    global running
    
    # Create a dummy license file for testing
    with open("dummy-license.dat", "w") as f:
        f.write("This is a dummy license file for testing")
    
    # Test the client with autodiscovery
    success = await test_client_autodiscovery()
    
    # Remove the dummy license file
    try:
        os.remove("dummy-license.dat")
    except:
        pass
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
        running = False
        sys.exit(0)
