#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example usage of the Gluesync Python SDK.

This script demonstrates how to use the Gluesync SDK to establish a connection to the CoreHub,
perform the handshake, and handle events.
"""

import asyncio
import logging
import sys
import os
import signal

from Gluesync_sdk import (
    GluesyncClient,
    GluesyncError,
    GluesyncConnectionError,
    GluesyncAuthenticationError,
    GluesyncLicenseError
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Gluesync-example")

# Configuration
HOST = "127.0.0.1"  # CoreHub hostname or IP
PORT = 1717  # CoreHub port
LICENSE_FILE = "gs-license.dat"  # Path to license file
MODULE_TAG = "example-python-module"  # Module tag/name
USE_SSL = False  # Whether to use SSL
KEYSTORE_PATH = None  # Path to JKS keystore file (if USE_SSL is True)
KEYSTORE_PASSWORD = None  # Password for JKS keystore (if USE_SSL is True)

# Global client instance
client = None


async def on_connected(token):
    """
    Handle the connected event.
    
    Args:
        token: The JWT token received from the server
    """
    logger.info(f"Connected to CoreHub successfully! Token: {token[:10]}...")
    logger.info("Press Ctrl+C to disconnect and exit.")


async def on_disconnected(reason):
    """
    Handle the disconnected event.
    
    Args:
        reason: The reason for disconnection
    """
    logger.info(f"Disconnected from CoreHub: {reason}")


async def on_error(error):
    """
    Handle the error event.
    
    Args:
        error: The exception that occurred
    """
    logger.error(f"Error in connection: {error}")


async def shutdown(signal, loop):
    """
    Handle the shutdown signal.
    
    Args:
        signal: Signal that triggered the shutdown
        loop: Event loop to close
    """
    logger.info(f"Received shutdown signal: {signal}")
    if client and client.is_connected:
        logger.info("Disconnecting from CoreHub...")
        await client.disconnect()
    
    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    loop.stop()


async def main():
    """
    Main entry point for the example.
    """
    global client
    
    try:
        # Create the client
        client = GluesyncClient(
            host=HOST,
            port=PORT,
            license_file_path=LICENSE_FILE,
            module_tag=MODULE_TAG,
            ssl=USE_SSL,
            keystore_path=KEYSTORE_PATH,
            keystore_password=KEYSTORE_PASSWORD
        )
        
        # Set up event handlers
        client.on_connected = on_connected
        client.on_disconnected = on_disconnected
        client.on_error = on_error
        
        # Connect to CoreHub
        logger.info(f"Connecting to CoreHub at {HOST}:{PORT}...")
        await client.connect()
        
        # Keep the connection open until user interrupts
        while client.is_connected:
            await asyncio.sleep(1)
        
    except GluesyncLicenseError as e:
        logger.error(f"License error: {e}")
        return 1
        
    except GluesyncAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return 1
        
    except GluesyncConnectionError as e:
        logger.error(f"Connection error: {e}")
        return 1
        
    except GluesyncError as e:
        logger.error(f"Gluesync error: {e}")
        return 1
        
    except KeyboardInterrupt:
        logger.info("User interrupted the program.")
        if client and client.is_connected:
            await client.disconnect()
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
        
    finally:
        if client and client.is_connected:
            logger.info("Disconnecting from CoreHub...")
            await client.disconnect()
        
    logger.info("Example completed successfully.")
    return 0


if __name__ == "__main__":
    # Set up the event loop
    loop = asyncio.get_event_loop()
    
    # Set up signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )
    
    # Run the main function
    try:
        exit_code = loop.run_until_complete(main())
        sys.exit(exit_code)
    finally:
        loop.close()
