# DomainTunnelLink (DTL)
Running DomainTunnelLink public demo on https://t.yazaar.xyz

Create direct links between locally hosted TCP or web services to a publically accessible host.

- Host `tunnelHost.py` on a public host and setup tunnel_servers.csv with domains and ports which are allowed exposure

- Run `tunnelClient.py` on a privately accessible server to expose an IP + port via a public host

## Requirements
Running on zero third-party dependencies! Run with Python 3.12 and you are good to go (older versions partially supported - try it)

### Optional requirements:
- aiohttp: more production driven HTTP server for DTL Authentication website

## Server setup

### tunnelServers definition

The file `tunnel_servers.csv` (located at root) is used to define which subdomans (and domains) are provided for claim, together with the required authentication for claim access. The client is required to provide the authentication password in order to claim a defined server.

Helper function to generate `sha256hex` and `salt` for `tunnel_servers.csv`

```bash
python tunnelHost.py --sha256gen 1 --auth x --salt y
```

Example `tunnel_servers.csv` file (sha256hex from example above)

```
type,con,sha256hex,salt
tcp,25565,769a4e6d0003189c7e96c5d9b7e810a0d11c3a12832527ec94b0f86d277f51ca,y
http,website.yazaar.xyz,769a4e6d0003189c7e96c5d9b7e810a0d11c3a12832527ec94b0f86d277f51ca,y
```

- Example use of TCP 25565: Run Minecraft server

- Example use of HTTP website.yazaar.xyz: Host a website on http(s)://website.yazaar.xyz

### HTTP IP headers definition

The headers used for IP identification can be defined dynamically within the file `http_ip_headers.csv` (located at root)

Example of header definitions:

```
name,type
x-forwarded-for,array
X-Forwarded-For,array
X-Real-Ip,text
```

The HTTP server (DTL Authorization website) is probably reading it case sensitive with capitalizations but my underlying socket integration for http authentication read all header values lowercase for easier predictibility (always, since the HTTP standard technically is case-insensitive).

## Expose locally running website
```bash
python tunnelClient.py --appType http --appHost localhost --appPort website.yazaar.xyz --appAuth secret --serverHost yazaar.xyz --serverTarget 25565 --serverAuth 8gC44Z23Lfz
```

### Client fields
Fields provided to tunnelClient.py by --field value (any order)

| Field | Required | Description |
| ----- | -------- | ----------- |
| appType | Yes (tcp/http) | If you are to host a TCP or HTTP server |
| appHost | Yes | The local host you would like to expose (i.e ip or localhost) |
| appPort | Yes | The local port of the host you would like to expose |
| appAuth | No | If you would like to keep the server private. Have to authenticate through the authentication website by providing a password, leading to the IP being whitelisted to access the server |
| serverHost | Yes | The public host which run tunnelHost.py |
| serverTarget | Yes | The resource you would like to claim and bind locally running service to (port or web domain) |
| serverAuth | Yes | The password which the resource is locked behind (password behind the sha256hex within tunnel_servers.csv) |
| serverAuth | Yes | The password which the resource is locked behind (auth password behind the sha256hex within tunnel_servers.csv) |
| bridgePort | No (default 9000) | The port which tunnelClient should connect to, in order to handshake with the server (usually running on 9000 unless modified) |
