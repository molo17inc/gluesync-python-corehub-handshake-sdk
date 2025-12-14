#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the ping-pong mechanism in the Gluesync SDK.
This script connects to a CoreHub and logs all ping-pong messages.
"""

import asyncio
import logging
import signal
import sys
import os
from gluesync_sdk import GluesyncClient

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all messages including ping-pong
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Explicitly set logging levels for specific modules
logging.getLogger('Gluesync.connection').setLevel(logging.DEBUG)
logging.getLogger('websockets').setLevel(logging.DEBUG)

# Create a logger for this script
logger = logging.getLogger("ping-pong-test")

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

async def main():
    client = None
    try:
        logger.info("Using UDP autodiscovery to find CoreHub...")
        
        # Create a client with autodiscovery
        client = GluesyncClient(
            host=None,  # Use autodiscovery
            port=1717,
            license_file_path="gs-license.dat",  # Update with your license file if needed
            module_tag="ping-pong-test",
            ssl=False,
            ping_interval=2.0  # Set a shorter ping interval for testing
        )
        
        logger.info(f"Connecting to CoreHub...")
        await client.connect()
        logger.info(f"Connected to CoreHub successfully! Token: {client.token[:10]}...")
        
        logger.info("Monitoring ping-pong messages. Press Ctrl+C to exit.")
        logger.info("You should see 'Sent ping' and 'Received pong' messages in the logs.")
        
        # Keep the connection alive and monitor for ping-pong messages
        while not shutdown_requested:
            await asyncio.sleep(1)
            
        logger.info("Shutdown requested, disconnecting...")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        # Clean up
        if client and client.is_connected:
            logger.info("Disconnecting from CoreHub...")
            try:
                await client.disconnect()
                logger.info("Disconnected from CoreHub")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
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
