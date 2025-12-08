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
tcp,6001,37268335dd6931045bdcdf92623ff819a64244b53d0e746d438797349d4da578,test
http,test.example.local,37268335dd6931045bdcdf92623ff819a64244b53d0e746d438797349d4da578,test
udp,5001,37268335dd6931045bdcdf92623ff819a64244b53d0e746d438797349d4da578,test
```

### Step-by-step Testing

#### 1. Terminal 1 - Start Demo Server
```bash
# Start TCP echo server
python test/apps/tcp_echo_server.py 6000
```

#### 2. Terminal 2 - Start TunnelHost
```bash
python tunnelHost.py
```

#### 3. Terminal 3 - Start TunnelClient
```bash
python tunnelClient.py --appType tcp --appHost 127.0.0.1 --appPort 6000 --serverHost 127.0.0.1 --serverTarget 6001 --serverAuth test
```

#### 4. Terminal 4 - Test Through Tunnel
```bash
python test/apps/tcp_client.py --port 6001 --message "Test message"
```

You should see:
- Client
  - Sending: Test message
  - Received: Echo: Test message
- Server (12345 is a random port allocated by the OS)
  - Received from ('127.0.0.1', 12345): Test message
  - Sent to ('127.0.0.1', 12345): Echo: Test message

## Command Line Options

### TCP Client
```bash
python test/apps/tcp_client.py [OPTIONS]

Options:
  --host HOST           Target host (default: 127.0.0.1)
  --port PORT           Target port (default: 6000)
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
