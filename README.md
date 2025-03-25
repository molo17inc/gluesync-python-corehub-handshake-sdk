# Gluesync Python SDK

A Python client-side SDK for connecting to Gluesync CoreHub services. This SDK enables external modules to establish authenticated WebSocket connections with Gluesync CoreHub, implementing the handshake process required for secure communication.

## Features

- **Secure WebSocket Connections**: Support for both WS and WSS using JKS certificates
- **Automated Handshake Process**: Handles the complete authentication flow with Gluesync CoreHub
- **License Management**: Validates and processes license files required for authentication
- **Keep-Alive Mechanism**: Implements ping/pong protocol to maintain persistent connections
- **UDP Autodiscovery**: Automatically discovers CoreHub on the local network
- **Async Support**: Built on top of modern async Python frameworks
- **Cross-Platform Compatibility**: Works on Linux, macOS, and Windows

## Installation

```bash
pip install gluesync-sdk
```

## Quick Start

```python
import asyncio
from gluesync_sdk import GluesyncClient

async def main():
    # Initialize the client with CoreHub address and license file path
    # For fixed address:
    client = GluesyncClient(
        host="localhost", 
        port=1717,
        license_file_path="/path/to/gs-license.dat",
        module_tag="my-module",
        use_ssl=True,  # Enable SSL/TLS
        verify_ssl=False  # Disable SSL certificate verification
    )
    
    # Or use UDP autodiscovery (set host to None)
    # client = GluesyncClient(
    #    host=None,  # Will use UDP autodiscovery to find CoreHub
    #    port=1717,
    #    license_file_path="/path/to/gs-license.dat",
    #    module_tag="my-module",
    #    use_ssl=True,  # Enable SSL/TLS
    #    verify_ssl=False  # Disable SSL certificate verification
    # )
    
    # Connect to CoreHub
    await client.connect()
    
    # The JWT token for API requests is available after connection
    jwt_token = client.token
    print(f"Connected with token: {jwt_token}")
    
    # Do your work here
    
    # Disconnect when done
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage

### Using UDP Autodiscovery

The SDK can automatically discover CoreHub on the local network using UDP:

```python
import asyncio
from gluesync_sdk import GluesyncClient

async def main():
    # Initialize the client without specifying a host to use autodiscovery
    client = GluesyncClient(
        # host parameter is omitted to enable autodiscovery
        license_file_path="/path/to/gs-license.dat",
        module_tag="my-module"
    )
    
    # Connect will automatically discover the CoreHub on the network
    await client.connect()
    
    # Do your work here
    
    # Disconnect when done
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

You can also use the environment variable `CORE_HUB_ADDRESS` to bypass autodiscovery:

```python
import os

# Set this to bypass autodiscovery
os.environ["CORE_HUB_ADDRESS"] = "192.168.1.100"
```

### Using SSL/TLS with JKS Certificates

```python
import asyncio
from gluesync_sdk import GluesyncClient

async def main():
    client = GluesyncClient(
        host="corehub.example.com", 
        port=1717,
        license_file_path="/path/to/gs-license.dat",
        module_tag="my-module",
        ssl=True,
        keystore_path="/path/to/Gluesync.com.jks",
        keystore_password="your-password"
    )
    
    await client.connect()
    # ...

if __name__ == "__main__":
    asyncio.run(main())
```

### Setting Up Event Handlers

```python
import asyncio
from gluesync_sdk import GluesyncClient

async def on_connected(token):
    print(f"Connected! Received token: {token}")

async def on_disconnected(reason):
    print(f"Disconnected: {reason}")

async def on_error(error):
    print(f"Error: {error}")

async def main():
    client = GluesyncClient(
        host="localhost", 
        port=1717,
        license_file_path="/path/to/gs-license.dat",
        module_tag="my-module"
    )
    
    # Set up event handlers
    client.on_connected = on_connected
    client.on_disconnected = on_disconnected
    client.on_error = on_error
    
    await client.connect()
    
    # Keep the connection alive for some time
    await asyncio.sleep(3600)
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### `GluesyncClient`

The main class for interacting with Gluesync CoreHub.

#### Constructor Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| host | str | No | None | The hostname or IP of the CoreHub. If None, autodiscovery will be used |
| port | int | No | 1717 | The port number for the CoreHub WebSocket |
| license_file_path | str | No | "gs-license.dat" | Path to the gs-license.dat file |
| module_tag | str | No | "python-module" | The module identifier tag |
| ssl | bool | No | False | Whether to use SSL/TLS |
| keystore_path | str | No | None | Path to JKS keystore file (required if ssl=True) |
| keystore_password | str | No | None | Password for the JKS keystore |
| ping_interval | float | No | 1.0 | Interval in seconds between ping messages |
| timeout | float | No | 10.0 | Connection timeout in seconds |
| discovery_start_port | int | No | 1717 | The base port number for UDP discovery |
| discovery_port_range | int | No | 10 | Number of ports to scan for UDP discovery |

#### Methods

- **`connect()`**: Establishes a WebSocket connection to the CoreHub
- **`disconnect()`**: Closes the WebSocket connection
- **`is_connected()`**: Returns the connection status
- **`get_token()`**: Returns the JWT token received from CoreHub

#### Properties

- **`token`**: The JWT token received from CoreHub
- **`connection_status`**: Current status of the connection

#### Event Handlers

- **`on_connected(token)`**: Called when connection is successfully established
- **`on_disconnected(reason)`**: Called when connection is closed
- **`on_error(error)`**: Called when an error occurs

## Advanced Usage

### UDP Autodiscovery

The SDK can automatically discover the CoreHub on the network using UDP broadcasts:

```python
# Create a client that will use autodiscovery
client = GluesyncClient(
    host=None,  # Setting host to None enables autodiscovery
    port=1717,
    license_file_path="/path/to/gs-license.dat",
    module_tag="my-module",
    discovery_start_port=1717,  # Base port for discovery
    discovery_port_range=10      # Number of ports to scan
)

# The CoreHub address will be discovered during connect()
await client.connect()
```

### Connection Resilience

Implement an automatic reconnection strategy for your application:

```python
import asyncio
from gluesync_sdk import GluesyncClient

# Reconnection settings
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 2.0  # Base delay in seconds
reconnecting = False

async def on_disconnected(reason):
    """Handle disconnection and trigger reconnection"""
    global reconnecting
    print(f"Disconnected: {reason}")
    
    if not reconnecting:
        reconnecting = True
        asyncio.create_task(attempt_reconnect())

async def attempt_reconnect():
    """Attempt to reconnect with exponential backoff"""
    global client, reconnecting
    attempt = 0
    
    while reconnecting and (attempt < MAX_RECONNECT_ATTEMPTS):
        attempt += 1
        delay = min(RECONNECT_DELAY * (2 ** (attempt - 1)), 30)  # Exponential backoff
        
        print(f"Reconnecting in {delay:.1f} seconds (attempt {attempt}/{MAX_RECONNECT_ATTEMPTS})")
        await asyncio.sleep(delay)
        
        try:
            await client.connect()
            print("Reconnected successfully!")
            reconnecting = False
            break
        except Exception as e:
            print(f"Reconnection failed: {e}")
    
    if reconnecting:
        print(f"Failed to reconnect after {MAX_RECONNECT_ATTEMPTS} attempts")
        reconnecting = False

async def main():
    global client
    
    client = GluesyncClient(
        host=None,  # Use autodiscovery
        license_file_path="/path/to/gs-license.dat",
        module_tag="resilient-module"
    )
    
    # Register the disconnection handler
    client.on_disconnected = on_disconnected
    
    try:
        await client.connect()
        print(f"Connected with token: {client.token[:10]}...")
        
        # Keep the application running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        await client.disconnect()
        print("Disconnected")
```

## Error Handling

The SDK defines several exception types to handle different error scenarios:

- **`GluesyncConnectionError`**: Base exception for connection issues
- **`GluesyncAuthenticationError`**: Authentication failed
- **`GluesyncLicenseError`**: License is invalid or expired
- **`GluesyncTimeoutError`**: Connection or operation timed out

Example:

```python
import asyncio
from gluesync_sdk import GluesyncClient
from gluesync_sdk.exceptions import GluesyncAuthenticationError, GluesyncLicenseError

async def main():
    try:
        client = GluesyncClient(
            host="localhost", 
            port=1717,
            license_file_path="/path/to/gs-license.dat",
            module_tag="my-module"
        )
        
        await client.connect()
        # ...
        
    except GluesyncAuthenticationError as e:
        print(f"Authentication failed: {e}")
    except GluesyncLicenseError as e:
        print(f"License error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## License

This project is dual-licensed under:

1. **GNU General Public License (GPL) Version 3** - Available at no cost, but any derivative works must also be licensed under GPL v3.

2. **MOLO17 Commercial License** - For proprietary use, includes warranty. Contact MOLO17 at [info@molo17.com](mailto:info@molo17.com) for licensing terms and conditions.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For support, please contact MOLO17 at [info@molo17.com](mailto:info@molo17.com).
