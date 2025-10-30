#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for connection interruption in the Gluesync SDK.
This script tests how the client behaves when the CoreHub becomes unavailable
or closes the connection.
"""

import asyncio
import logging
import signal
import sys
import os
import time
from typing import Optional, Dict, Any, Callable

# Add the parent directory to sys.path to import the SDK
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gluesync_sdk import GluesyncClient
from gluesync_sdk.exceptions import GluesyncConnectionError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Explicitly set logging levels for specific modules
logging.getLogger('Gluesync.connection').setLevel(logging.DEBUG)
logging.getLogger('Gluesync.client').setLevel(logging.DEBUG)

# Create a logger for this script
logger = logging.getLogger("connection-interruption-test")

# Global flag for shutdown
shutdown_requested = False

# Handle Ctrl+C
def signal_handler(sig, frame):
    global shutdown_requested
    logger.info(f"Received shutdown signal: {sig}")
    shutdown_requested = True

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class EventCounter:
    """Simple class to count and log events."""
    
    def __init__(self, name: str):
        self.name = name
        self.count = 0
        self.last_event_time = None
        self.last_event_data = None
    
    def increment(self, data: Any = None):
        """Increment the counter and store the event data."""
        self.count += 1
        self.last_event_time = time.time()
        self.last_event_data = data
        logger.info(f"{self.name} event #{self.count}: {data}")
        return self.count

async def main():
    """
    Main test function.
    """
    client = None
    
    # Create event counters
    disconnection_counter = EventCounter("Disconnection")
    error_counter = EventCounter("Error")
    
    # Define callback handlers
    async def on_disconnected(reason: str):
        disconnection_counter.increment(reason)
        logger.warning(f"Connection lost: {reason}")
    
    async def on_error(error: Exception):
        error_counter.increment(str(error))
        logger.error(f"Error received: {error}")
    
    try:
        logger.info("Creating a client to test connection interruption...")
        
        # Create the client
        client = GluesyncClient(
            host=None,  # Use autodiscovery
            module_tag="interruption-test",
            license_file_path="dummy-license.dat"  # Use a dummy path for testing
        )
        
        # Mock the license content method to bypass license file check
        client._get_license_content = lambda: "mock-license-content"
        
        # Connect to CoreHub - this initializes the connection object
        logger.info("Connecting to CoreHub...")
        await client.connect()
        
        # Register callbacks after connection is established
        client._connection.on_disconnected = on_disconnected
        client._connection.on_error = on_error
        
        logger.info(f"Connected to CoreHub successfully!")
        logger.info("Now monitoring the connection for interruptions...")
        logger.info("You can test interruptions by:")
        logger.info("1. Stop the CoreHub service")
        logger.info("2. Temporarily block network access")
        logger.info("3. Simulate different network conditions")
        logger.info("Press Ctrl+C to exit")
        
        # Main loop to monitor the connection
        while not shutdown_requested:
            connection_status = "Connected" if client.is_connected else "Disconnected"
            stats = (
                f"Connection: {connection_status}, "
                f"Disconnections: {disconnection_counter.count}, "
                f"Errors: {error_counter.count}"
            )
            logger.info(stats)
            
            # If disconnected and we've observed at least one disconnection,
            # try to connect again
            if not client.is_connected and disconnection_counter.count > 0:
                disconnect_time = disconnection_counter.last_event_time
                current_time = time.time()
                elapsed = current_time - disconnect_time if disconnect_time else 0
                
                # Wait at least 5 seconds before trying to reconnect
                if elapsed >= 5:
                    logger.info("Attempting to reconnect...")
                    try:
                        await client.connect()
                        logger.info("Reconnected successfully!")
                    except Exception as e:
                        logger.error(f"Failed to reconnect: {e}")
            
            await asyncio.sleep(2)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        # Clean up
        if client and client.is_connected:
            logger.info("Disconnecting client...")
            await client.disconnect()
            logger.info("Client disconnected")
    
    return 0

if __name__ == "__main__":
    try:
        # Get the event loop
        loop = asyncio.get_event_loop()
        
        # Run the main function
        exit_code = loop.run_until_complete(main())
        
        # Clean up and exit
        loop.close()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)
