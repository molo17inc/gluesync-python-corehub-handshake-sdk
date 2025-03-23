#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example usage of the Gluesync Python SDK.

This script demonstrates how to use the Gluesync SDK to establish a connection to the CoreHub,
perform the handshake, handle events, and implement connection resilience.

Key features demonstrated:
1. UDP Autodiscovery - Finding CoreHub on the network automatically
2. Connection Event Handling - Managing connection, disconnection, and error events
3. Reconnection Strategy - Handling connection failures with automatic retries
"""

import asyncio
import logging
import sys
import os
import signal

from gluesync_sdk import (
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
# Set HOST to None to use UDP autodiscovery - the SDK will automatically
# discover CoreHub on the network using UDP broadcast messages
# Or set a specific IP address to bypass autodiscovery
# HOST = "127.0.0.1"  # Fixed CoreHub hostname or IP
HOST = os.environ.get("CORE_HUB_ADDRESS", None)  # Use env var or autodiscovery
PORT = 1717  # CoreHub port
LICENSE_FILE = "gs-license.dat"  # Path to license file
MODULE_TAG = "example-python-module"  # Module tag/name

# SSL Configuration - Choose one of the following approaches:

# Approach 1: Direct SSL parameters
USE_SSL = False  # Whether to use SSL
KEYSTORE_PATH = None  # Path to JKS keystore file (if USE_SSL is True)
KEYSTORE_PASSWORD = None  # Password for JKS keystore (if USE_SSL is True)

# Approach 2: Using security_config.json file
# This is the recommended approach as it contains all necessary SSL parameters
SECURITY_CONFIG = "security-config.json"  # Path to security config file

# Reconnection settings
MAX_RECONNECT_ATTEMPTS = 5  # Number of reconnection attempts (0 for infinite)
RECONNECT_DELAY = 2.0  # Delay between reconnection attempts in seconds

# Global client instance
client = None

# Reconnection state
reconnecting = False
reconnect_attempt = 0


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
    Handle the disconnected event and trigger reconnection.
    
    Args:
        reason: The reason for disconnection
    """
    global reconnecting
    
    logger.info(f"Disconnected from CoreHub: {reason}")
    
    # Start reconnection if not already reconnecting
    if not reconnecting:
        reconnecting = True
        asyncio.create_task(attempt_reconnect())


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


async def attempt_reconnect():
    """
    Attempt to reconnect to CoreHub with exponential backoff.
    """
    global client, reconnecting, reconnect_attempt
    
    reconnect_attempt = 0
    
    while reconnecting and (MAX_RECONNECT_ATTEMPTS == 0 or reconnect_attempt < MAX_RECONNECT_ATTEMPTS):
        reconnect_attempt += 1
        
        delay = min(RECONNECT_DELAY * (2 ** (reconnect_attempt - 1)), 30)  # Exponential backoff, max 30 seconds
        
        # Wait before attempting to reconnect
        logger.info(f"Waiting {delay:.1f} seconds before reconnection attempt {reconnect_attempt}")
        await asyncio.sleep(delay)
        
        if not reconnecting:
            break
        
        try:
            logger.info(f"Reconnection attempt {reconnect_attempt}" + 
                       (f"/{MAX_RECONNECT_ATTEMPTS}" if MAX_RECONNECT_ATTEMPTS > 0 else ""))
            
            # Connect to CoreHub
            if not client.is_connected:
                await client.connect()
                
                logger.info(f"Successfully reconnected to CoreHub after {reconnect_attempt} attempts")
                reconnecting = False
                reconnect_attempt = 0
                break
                
        except Exception as e:
            logger.error(f"Reconnection attempt {reconnect_attempt} failed: {e}")
    
    if reconnecting and MAX_RECONNECT_ATTEMPTS > 0 and reconnect_attempt >= MAX_RECONNECT_ATTEMPTS:
        logger.error(f"Failed to reconnect after {MAX_RECONNECT_ATTEMPTS} attempts")
        reconnecting = False

async def main():
    """
    Main entry point for the example.
    """
    global client
    
    try:
        # Create the client
        # Uncomment the appropriate client creation approach based on your needs:
        
        # Approach 1: Using direct SSL parameters
        client = GluesyncClient(
            host=HOST,  # If None, will use UDP autodiscovery
            port=PORT,
            license_file_path=LICENSE_FILE,
            module_tag=MODULE_TAG,
            ssl=USE_SSL,
            keystore_path=KEYSTORE_PATH,
            keystore_password=KEYSTORE_PASSWORD
        )
        
        # Approach 2: Using security_config.json file (recommended)
        # client = GluesyncClient(
        #     host=HOST,  # If None, will use UDP autodiscovery
        #     port=PORT,
        #     license_file_path=LICENSE_FILE,
        #     module_tag=MODULE_TAG,
        #     ssl=True,  # Set to True to enable SSL
        #     security_config=SECURITY_CONFIG  # Path to security-config.json
        # )
        
        if HOST is None:
            logger.info("Using UDP autodiscovery to find CoreHub...")
            logger.info("The SDK will listen for UDP broadcast messages to discover CoreHub's address")
        else:
            logger.info(f"Using provided CoreHub address: {HOST}")
        
        # Set up event handlers
        client.on_connected = on_connected
        client.on_disconnected = on_disconnected
        client.on_error = on_error
        
        # Connect to CoreHub
        logger.info(f"Connecting to CoreHub...")
        await client.connect()
        
        # If we're connected, the host may have been discovered via UDP
        discovered_host = getattr(client, '_host', HOST)
        logger.info(f"Connected to CoreHub at {discovered_host}:{PORT}")
        
        # Keep the connection open until user interrupts
        while True:
            if client.is_connected:
                logger.info("Connection status: Connected")
            else:
                logger.info("Connection status: Disconnected")
            
            await asyncio.sleep(5)
        
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
