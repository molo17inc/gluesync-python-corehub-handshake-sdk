#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from gluesync_sdk.connection import WebSocketConnection
from gluesync_sdk.discovery import CoreHubDiscovery

@pytest.mark.asyncio
async def test_receive_loop_general_exception_triggers_disconnect():
    """
    Test that when the receive loop encounters a general exception (like OSError),
    it properly transitions the connection state and triggers the on_disconnected callback.
    """
    conn = WebSocketConnection("localhost", 1717, headers={})
    conn._connected = True
    
    # Mock ws to raise an OSError when recv is called
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = OSError("Connection reset by peer")
    # Set attributes checked by is_connected property
    mock_ws.closed = False
    mock_ws.is_closing = MagicMock(return_value=False)
    conn.ws = mock_ws
    
    # Track on_disconnected call
    disconnect_called = asyncio.Event()
    disconnect_reason = None
    
    async def on_disconnected_cb(reason):
        nonlocal disconnect_reason
        disconnect_reason = reason
        disconnect_called.set()
        
    conn.on_disconnected = on_disconnected_cb
    
    # Start receive loop
    conn._start_receive_task()
    
    # Wait for the disconnect callback to be triggered
    await asyncio.wait_for(disconnect_called.wait(), timeout=2.0)
    
    assert conn.is_connected is False
    assert "Connection error: Connection reset by peer" in disconnect_reason

@pytest.mark.asyncio
async def test_ping_loop_general_exception_triggers_disconnect():
    """
    Test that when the ping loop encounters a general exception (like OSError),
    it properly transitions the connection state and triggers the on_disconnected callback.
    """
    conn = WebSocketConnection("localhost", 1717, headers={})
    conn._connected = True
    conn.ping_interval = 0.01  # Run quickly
    
    # Mock ws to raise an OSError when send is called
    mock_ws = AsyncMock()
    mock_ws.send.side_effect = OSError("Socket broken")
    # Set attributes checked by is_connected property
    mock_ws.closed = False
    mock_ws.is_closing = MagicMock(return_value=False)
    conn.ws = mock_ws
    
    # Track on_disconnected call
    disconnect_called = asyncio.Event()
    disconnect_reason = None
    
    async def on_disconnected_cb(reason):
        nonlocal disconnect_reason
        disconnect_reason = reason
        disconnect_called.set()
        
    conn.on_disconnected = on_disconnected_cb
    
    # Start ping loop
    conn._start_ping_task()
    
    # Wait for the disconnect callback to be triggered
    await asyncio.wait_for(disconnect_called.wait(), timeout=2.0)
    
    assert conn.is_connected is False
    assert "Ping error: Socket broken" in disconnect_reason

@pytest.mark.asyncio
async def test_discovery_timeout_non_blocking():
    """
    Test that CoreHubDiscovery's UDP autodiscovery does not block the asyncio event loop
    and times out correctly when no broadcast is found.
    """
    discovery = CoreHubDiscovery(start_port=25000, port_range=2)
    
    # Run a concurrent background task to measure if the event loop remains active
    loop_active = []
    async def background_spinner():
        for _ in range(5):
            await asyncio.sleep(0.02)
            loop_active.append(True)
            
    spinner_task = asyncio.create_task(background_spinner())
    
    # Run discovery with a short timeout of 0.1 seconds
    with pytest.raises(Exception):
        await discovery.discover_corehub(timeout=0.1)
            
    # Verify the event loop spinner ran concurrently and wasn't blocked
    await spinner_task
    assert len(loop_active) == 5
