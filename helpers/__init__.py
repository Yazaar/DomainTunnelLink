"""Helper utilities for DomainTunnelLink.

This package provides utility functions and classes for networking, data processing,
and general helper functionality used throughout the application.

Modules:
- misc: General utility functions (serialization, logging, etc)
- csvReader: CSV file parsing
- socketWrapper: TCP socket wrapper with buffering
- socketClient: TCP client connection helper
- socketHost: TCP server listener
- socketRegistry: Connection registry for tracking clients
"""

from helpers.misc import (
    serialize,
    deserialize,
    sha256,
    sha256_match,
    new_uuid,
    validate_port,
    to_int,
    find_first,
    seconds_since,
    load_argv,
    get_file,
    queue_task,
    http_response,
    get_http_headers,
    http_identification,
    get_ip,
)

from helpers.csvReader import CSVReader
from helpers.socketWrapper import SocketWrapper
from helpers.socketClient import SocketClient
from helpers.socketHost import SocketHost
from helpers.socketHost import create_host
from helpers.socketRegistry import SocketRegistry

__all__ = [
    # misc exports
    'serialize',
    'deserialize',
    'sha256',
    'sha256_match',
    'new_uuid',
    'validate_port',
    'to_int',
    'find_first',
    'seconds_since',
    'load_argv',
    'get_file',
    'queue_task',
    'http_response',
    'get_http_headers',
    'http_identification',
    'get_ip',
    'create_host',
    # Classes
    'CSVReader',
    'SocketWrapper',
    'SocketClient',
    'SocketHost',
    'SocketRegistry',
]
