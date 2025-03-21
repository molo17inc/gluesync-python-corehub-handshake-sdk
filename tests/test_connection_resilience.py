#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for connection resilience in the GlueSync SDK.
This script tests how the client behaves when the CoreHub becomes unavailable
and demonstrates how to implement a reconnection strategy.
"""

import asyncio
import logging
import signal
import sys
import os
import time
from typing import Optional

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
logger = logging.getLogger("connection-resilience-test")

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

class ResilientClient:
    """
    A wrapper around GluesyncClient that adds automatic reconnection.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 1717,
        license_file_path: str = "gs-license.dat",
        module_tag: str = "resilient-client",
        ssl: bool = False,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0
    ):
        """
        Initialize the resilient client.
        
        Args:
            host: Hostname or IP address of the CoreHub (None for autodiscovery)
            port: Port number for the CoreHub WebSocket
            license_file_path: Path to the gs-license.dat file
            module_tag: Name/tag for this module
            ssl: Whether to use SSL/TLS for the connection
            reconnect_attempts: Number of reconnection attempts (0 for infinite)
            reconnect_delay: Delay between reconnection attempts in seconds
        """
        self.host = host
        self.port = port
        self.license_file_path = license_file_path
        self.module_tag = module_tag
        self.ssl = ssl
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        # Create the client
        self.client = GluesyncClient(
            host=host,
            port=port,
            license_file_path=license_file_path,
            module_tag=module_tag,
            ssl=ssl
        )
        
        # Mock the license content method to bypass license file check
        self.client._get_license_content = lambda: "mock-license-content"
        
        # Internal state
        self._connected = False
        self._reconnecting = False
        self._reconnect_task = None
        self._connection_lost_time = None
        self._attempt_count = 0
        
        # Set up callbacks
        self.client._connection.on_disconnected = self._handle_disconnection
    
    @property
    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self._connected and self.client.is_connected
    
    async def connect(self):
        """
        Connect to the CoreHub with automatic reconnection.
        """
        try:
            await self.client.connect()
            self._connected = True
            self._attempt_count = 0
            logger.info("Connected to CoreHub successfully")
            return self.client.token
        except Exception as e:
            logger.error(f"Error connecting to CoreHub: {e}")
            await self._start_reconnection()
            raise
    
    async def disconnect(self):
        """
        Disconnect from the CoreHub.
        """
        self._connected = False
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        
        if self.client.is_connected:
            await self.client.disconnect()
    
    async def _handle_disconnection(self, reason: str):
        """
        Handle a disconnection from the CoreHub.
        """
        self._connected = False
        self._connection_lost_time = time.time()
        logger.warning(f"Connection to CoreHub lost: {reason}")
        
        # Start the reconnection process
        await self._start_reconnection()
    
    async def _start_reconnection(self):
        """
        Start the reconnection process.
        """
        if self._reconnecting:
            return
        
        self._reconnecting = True
        self._attempt_count = 0
        
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())
    
    async def _reconnect_loop(self):
        """
        Reconnection loop.
        """
        while not self._connected and (self.reconnect_attempts == 0 or self._attempt_count < self.reconnect_attempts):
            self._attempt_count += 1
            
            try:
                if self.reconnect_attempts > 0:
                    logger.info(f"Reconnection attempt {self._attempt_count}/{self.reconnect_attempts}...")
                else:
                    logger.info(f"Reconnection attempt {self._attempt_count}...")
                
                # Create a new client instance
                self.client = GluesyncClient(
                    host=self.host,
                    port=self.port,
                    license_file_path=self.license_file_path,
                    module_tag=self.module_tag,
                    ssl=self.ssl
                )
                
                # Mock the license content method to bypass license file check
                self.client._get_license_content = lambda: "mock-license-content"
                
                # Set callback for disconnection
                self.client._connection.on_disconnected = self._handle_disconnection
                
                # Try to connect
                await self.client.connect()
                self._connected = True
                logger.info(f"Successfully reconnected to CoreHub after {self._attempt_count} attempts")
                break
                
            except Exception as e:
                logger.error(f"Reconnection attempt {self._attempt_count} failed: {e}")
                
                # Wait before trying again
                await asyncio.sleep(self.reconnect_delay)
        
        if not self._connected:
            logger.error(f"Failed to reconnect after {self._attempt_count} attempts")
        
        self._reconnecting = False

async def main():
    """
    Main test function.
    """
    client = None
    try:
        logger.info("Creating a resilient client with auto-reconnect capabilities...")
        
        # Create the resilient client
        client = ResilientClient(
            host=None,  # Use autodiscovery
            reconnect_attempts=3,
            reconnect_delay=2.0
        )
        
        # Connect to CoreHub
        logger.info("Connecting to CoreHub...")
        await client.connect()
        
        logger.info(f"Connected to CoreHub successfully!")
        logger.info("Now you can test the reconnection by:")
        logger.info("1. Stop the CoreHub service")
        logger.info("2. Watch the client attempt to reconnect")
        logger.info("3. Start the CoreHub service again to see if the client reconnects")
        logger.info("Press Ctrl+C to exit")
        
        # Keep running until shutdown is requested
        while not shutdown_requested:
            logger.info(f"Connection status: {'Connected' if client.is_connected else 'Disconnected'}")
            await asyncio.sleep(5)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        # Clean up
        if client:
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
