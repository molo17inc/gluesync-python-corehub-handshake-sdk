# Gluesync Python SDK

A Python client-side SDK for connecting to Gluesync CoreHub services. This SDK enables external modules to establish authenticated WebSocket connections with Gluesync CoreHub, implementing the handshake process required for secure communication.

## Features

- **Secure WebSocket Connections**: Support for both WS and WSS using JKS certificates
- **Automated Handshake Process**: Handles the complete authentication flow with Gluesync CoreHub
- **License Management**: Validates and processes license files required for authentication
- **Keep-Alive Mechanism**: Implements ping/pong protocol to maintain persistent connections
- **Async Support**: Built on top of modern async Python frameworks
- **Cross-Platform Compatibility**: Works on Linux, macOS, and Windows

## Installation

```bash
pip install Gluesync-sdk
```

## Quick Start

```python
import asyncio
from Gluesync_sdk import GluesyncClient

async def main():
    # Initialize the client with CoreHub address and license file path
    client = GluesyncClient(
        host="localhost", 
        port=1717,
        license_file_path="/path/to/gs-license.dat",
        module_tag="my-module"
    )
    
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

### Using SSL/TLS with JKS Certificates

```python
import asyncio
from Gluesync_sdk import GluesyncClient

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
from Gluesync_sdk import GluesyncClient

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
| host | str | Yes | - | The hostname or IP of the CoreHub |
| port | int | Yes | - | The port number for the CoreHub WebSocket |
| license_file_path | str | Yes | - | Path to the gs-license.dat file |
| module_tag | str | Yes | - | The module identifier tag |
| ssl | bool | No | False | Whether to use SSL/TLS |
| keystore_path | str | No | None | Path to JKS keystore file (required if ssl=True) |
| keystore_password | str | No | None | Password for the JKS keystore |
| ping_interval | float | No | 1.0 | Interval in seconds between ping messages |
| timeout | float | No | 10.0 | Connection timeout in seconds |

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

## Error Handling

The SDK defines several exception types to handle different error scenarios:

- **`GluesyncConnectionError`**: Base exception for connection issues
- **`GluesyncAuthenticationError`**: Authentication failed
- **`GluesyncLicenseError`**: License is invalid or expired
- **`GluesyncTimeoutError`**: Connection or operation timed out

Example:

```python
import asyncio
from Gluesync_sdk import GluesyncClient
from Gluesync_sdk.exceptions import GluesyncAuthenticationError, GluesyncLicenseError

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

2. **MOLO17 Commercial License** - For proprietary use, includes warranty. Contact MOLO17 at info@molo17.com for licensing terms and conditions.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For support, please contact MOLO17 at info@molo17.com.