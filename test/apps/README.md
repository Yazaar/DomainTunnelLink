# Demo Applications for End-to-End Testing

This directory contains simple demo applications to test DomainTunnelLink protocols end-to-end.

## Applications

### TCP Protocol
- **tcp_echo_server.py** - Echo server that receives TCP messages and sends them back
- **tcp_client.py** - TCP client to send messages and receive responses

### UDP Protocol
- **udp_echo_server.py** - Echo server that receives UDP datagrams and sends them back
- **udp_client.py** - UDP client to send datagrams and receive responses

### HTTP Protocol
- **http_server.py** - Simple HTTP server that responds to GET/POST requests
- **http_client.py** - HTTP client to make GET/POST requests

## Quick Start

### Terminal 1: Start TCP Echo Server
```bash
python test/apps/tcp_echo_server.py 6000
```

Expected output:
```
TCP Echo Server started on 127.0.0.1:6000
```

### Terminal 2: Test TCP with Client
```bash
# Single message
python test/apps/tcp_client.py --port 6000 --message "Hello World"

# Or interactive mode (type messages, 'quit' to exit)
python test/apps/tcp_client.py --port 6000
```

---

### Terminal 1: Start UDP Echo Server
```bash
python test/apps/udp_echo_server.py 5000
```

Expected output:
```
UDP Echo Server started on 127.0.0.1:5000
```

### Terminal 2: Test UDP with Client
```bash
# Single message
python test/apps/udp_client.py --port 5000 --message "Hello World"

# Or interactive mode
python test/apps/udp_client.py --port 5000
```

---

### Terminal 1: Start HTTP Server
```bash
python test/apps/http_server.py 8000
```

Expected output:
```
HTTP Server started on 127.0.0.1:8000
```

### Terminal 2: Test HTTP with Client
```bash
# GET request
python test/apps/http_client.py --port 8000 --method GET --path /

# POST request
python test/apps/http_client.py --port 8000 --method POST --path /api --body "test"

# GET with custom domain header
python test/apps/http_client.py --port 8000 --domain test.example.com --path /api
```

## Testing with TunnelHost and TunnelClient

### Setup CSV Configuration

Edit `tunnel_servers.csv`:
```csv
type,con,sha256hex,salt
tcp,25565,1930a5b7ee4d6ca7d909ccf7fdaecfe544a895f138e290185fc918803c9904e8,good
http,test.yazaar.xyz,1930a5b7ee4d6ca7d909ccf7fdaecfe544a895f138e290185fc918803c9904e8,good
udp,5000,1930a5b7ee4d6ca7d909ccf7fdaecfe544a895f138e290185fc918803c9904e8,good
```

### Step-by-step Testing

#### 1. Terminal 1 - Start Demo Server
```bash
# Start TCP echo server
python test/apps/tcp_echo_server.py 25565
```

#### 2. Terminal 2 - Start TunnelHost
```bash
python tunnelHost.py
```

Expected output:
```
TunnelHost listening on 0.0.0.0:9000 (TCP)
TunnelHost listening on 0.0.0.0:8001 (HTTP)
```

#### 3. Terminal 3 - Start TunnelClient
```bash
python tunnelClient.py \
    --server-host 127.0.0.1 \
    --server-port 9000 \
    --app-host 127.0.0.1 \
    --app-port 25565 \
    --type tcp \
    --target 25565 \
    --password good
```

#### 4. Terminal 4 - Test Through Tunnel
```bash
# Connect through tunnel on a different port (tunnelClient listens on app-port)
python test/apps/tcp_client.py --port 25565 --message "Test message"
```

You should see:
- Server receives "Test message"
- Client receives "Echo: Test message"

## Command Line Options

### TCP Client
```bash
python test/apps/tcp_client.py [OPTIONS]

Options:
  --host HOST           Target host (default: 127.0.0.1)
  --port PORT           Target port (default: 25565)
  --message MESSAGE     Message to send (if not specified, enters interactive mode)
```

### UDP Client
```bash
python test/apps/udp_client.py [OPTIONS]

Options:
  --host HOST           Target host (default: 127.0.0.1)
  --port PORT           Target port (default: 5000)
  --message MESSAGE     Message to send (if not specified, enters interactive mode)
```

### HTTP Client
```bash
python test/apps/http_client.py [OPTIONS]

Options:
  --host HOST           Target host (default: 127.0.0.1)
  --port PORT           Target port (default: 8000)
  --path PATH           Request path (default: /)
  --method METHOD       HTTP method: GET or POST (default: GET)
  --body BODY           POST body (only for POST requests)
  --domain DOMAIN       Host header value (default: host:port)
```

### Echo Servers
```bash
python test/apps/tcp_echo_server.py [PORT]
python test/apps/udp_echo_server.py [PORT]
python test/apps/http_server.py [PORT]
```

## Example Scenarios

### Scenario 1: Direct Connection to Echo Server
```bash
# Terminal 1
python test/apps/tcp_echo_server.py 25565

# Terminal 2
python test/apps/tcp_client.py --port 25565 --message "Hello"
# Output: Echo: Hello
```

### Scenario 2: Through TunnelHost/TunnelClient

```bash
# Terminal 1 - Echo server (on original port)
python test/apps/tcp_echo_server.py 25565

# Terminal 2 - TunnelHost (listens on 9000)
python tunnelHost.py

# Terminal 3 - TunnelClient (connects to 9000, forwards to 25565)
python tunnelClient.py \
    --server-host 127.0.0.1 \
    --server-port 9000 \
    --app-host 127.0.0.1 \
    --app-port 25565 \
    --type tcp \
    --target 25565 \
    --password good

# Terminal 4 - Client connects to TunnelClient's app port (25565)
python test/apps/tcp_client.py --port 25565 --message "Hello through tunnel"
```

### Scenario 3: Multiple Tunnels

You can run multiple TunnelClient instances for different protocols:

```bash
# Terminal 3a - TCP tunnel
python tunnelClient.py \
    --server-host 127.0.0.1 \
    --server-port 9000 \
    --app-host 127.0.0.1 \
    --app-port 25565 \
    --type tcp \
    --target 25565 \
    --password good

# Terminal 3b - UDP tunnel (in another terminal)
python tunnelClient.py \
    --server-host 127.0.0.1 \
    --server-port 9000 \
    --app-host 127.0.0.1 \
    --app-port 5000 \
    --type udp \
    --target 5000 \
    --password good
```

## Logging

All applications use Python's logging module. By default, logs show:
- Timestamp
- Component name
- Log level
- Message

Example log output:
```
2025-12-06 10:30:45,123 - __main__ - INFO - TCP Echo Server started on 127.0.0.1:25565
2025-12-06 10:30:46,456 - __main__ - INFO - Client connected: ('127.0.0.1', 54321)
2025-12-06 10:30:46,789 - __main__ - INFO - Received from ('127.0.0.1', 54321): Hello
```

## Troubleshooting

### "Address already in use" error
The port is still in use. Wait a few seconds or use a different port.

```bash
python test/apps/tcp_echo_server.py 25566  # Use different port
```

### Connection refused
Make sure the server is running on the correct host and port.

```bash
# Check that server is listening
netstat -an | findstr LISTENING
```

### No response from client
- Check that server is running
- Check that the host and port are correct
- Check that firewall isn't blocking connections

## Testing Tips

1. **Use separate terminals** - Makes it easier to see logs from each component
2. **Start servers first** - Wait for "listening" message before connecting clients
3. **Use the same host** - 127.0.0.1 or localhost for local testing
4. **Test direct first** - Test server → client directly before testing through tunnel
5. **Monitor logs** - Keep terminals visible to see what's happening
6. **Test one protocol at a time** - TCP first, then UDP, then HTTP

## Next Steps

After testing with demo apps, consider:
1. Creating automated test scripts
2. Adding performance benchmarks
3. Testing with multiple concurrent connections
4. Testing with various message sizes
5. Testing error conditions (disconnect, timeout, etc.)

---

**Note**: These are simple demo applications for testing. For production use, add proper error handling, authentication, encryption, and monitoring.
