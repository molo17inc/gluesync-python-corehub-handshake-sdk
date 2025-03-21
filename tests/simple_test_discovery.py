#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple test script for UDP autodiscovery functionality.
This script will simulate both the CoreHub broadcast and client discovery.
"""

import asyncio
import socket
import threading
import time
import logging
import sys

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

# Flag to control the broadcast thread
running = True

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

async def listen_for_discovery():
    """
    Listen for discovery broadcasts on a random port.
    """
    import random
    
    # Choose a random port from the range to listen on
    port = random.choice(range(START_PORT + 1, START_PORT + PORT_RANGE + 1))
    
    logger.info(f"Listening for broadcasts on port {port}")
    
    # Create a UDP socket
    sock = None
    
    try:
        # Create and configure the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set socket timeout to prevent blocking forever
        sock.settimeout(5)
        
        # Try to bind to the chosen port
        sock.bind(("0.0.0.0", port))
        
        # Wait for a broadcast message
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                logger.debug(f"Received data from {addr[0]}: {data}")
                
                # Check if this is the expected discovery message
                if data == DISCOVERY_MESSAGE:
                    corehub_address = addr[0]
                    logger.info(f"CoreHub discovered at {corehub_address}")
                    return corehub_address
                
            except socket.timeout:
                logger.debug("No broadcast received, continuing to listen...")
                # We can use a sleep to prevent CPU spinning
                await asyncio.sleep(0.1)
                continue
                
    except Exception as e:
        logger.error(f"Error listening for discovery: {e}")
        return None
    finally:
        if sock:
            sock.close()

async def test_sdk_discovery():
    """
    Test the discovery functionality from the SDK.
    """
    try:
        from gluesync_sdk.discovery import CoreHubDiscovery, get_corehub_address
        
        logger.info("Testing CoreHubDiscovery from SDK...")
        discovery = CoreHubDiscovery(start_port=START_PORT, port_range=PORT_RANGE)
        
        try:
            # Try to discover the CoreHub
            corehub_address = await discovery.discover_corehub()
            logger.info(f"SUCCESS! CoreHub discovered at {corehub_address}")
            return True
        except Exception as e:
            logger.error(f"SDK discovery failed: {e}")
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import discovery module: {e}")
        return False

async def main():
    """
    Main entry point for the test script.
    """
    global running
    
    # Start the simulated CoreHub broadcast in a separate thread
    broadcast_thread = threading.Thread(target=simulate_corehub_broadcast)
    broadcast_thread.daemon = True
    broadcast_thread.start()
    
    # Give the broadcast a moment to start
    await asyncio.sleep(1)
    
    # First test our simple implementation
    logger.info("Testing simple discovery implementation...")
    simple_result = await listen_for_discovery()
    
    if simple_result:
        logger.info(f"Simple discovery successful! Found CoreHub at {simple_result}")
        
        # Now test the SDK implementation
        logger.info("Now testing SDK implementation...")
        sdk_result = await test_sdk_discovery()
        
        if sdk_result:
            logger.info("SDK discovery also successful!")
        else:
            logger.error("SDK discovery failed, but simple discovery worked.")
            logger.error("This suggests an issue with the SDK implementation.")
    else:
        logger.error("Simple discovery failed. This suggests a network or broadcast issue.")
    
    # Stop the broadcast thread
    running = False
    broadcast_thread.join(timeout=2)
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
        running = False
        sys.exit(0)
