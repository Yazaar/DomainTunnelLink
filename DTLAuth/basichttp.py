import http.server, socketserver, json, threading, asyncio, logging
from concurrent.futures import TimeoutError as FutureTimeout
from DTLAuth.utils import STATIC_FOLDER, TEMPLATE_FOLDER, AUTH_CALLBACK_TYPE, handle_auth_request, static_resolver
from helpers import misc

logger = logging.getLogger(__name__)

class BasicHttpHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open(TEMPLATE_FOLDER / 'index.html', 'r') as f:
                self.wfile.write(f.read().encode())
        elif self.path.startswith('/public'):
            mime_type = None
            content = None
            try:
                mime_type, content = static_resolver(self.path)
            except Exception:
                pass

            if content == None or mime_type == None:
                self.send_error(404, 'File path invalid')
                return

            encoded_content = None
            try:
                encoded_content = content.encode() if isinstance(content, str) else content
            except Exception:
                pass

            if encoded_content == None:
                self.send_error(404, 'File read error')
                return

            self.send_response(200)
            self.send_header('Content-type', mime_type)
            self.end_headers()
            self.wfile.write(encoded_content)
        else:
            logger.warning(f'Unhandled url path: {self.path}')
            self.send_error(404, "Unknown endpoint")

    def do_POST(self):
        if self.path == '/api/auth-resource':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
            except:
                self._json_response({'statusMessage': 'Failed to read data'})
                return

            ip = misc.get_ip(dict(self.headers), [self.client_address[0]])

            future = asyncio.run_coroutine_threadsafe(handle_auth_request(ip, data, _onResourceAuthCallback), _event_loop)
            resolvedAuth = None

            try:
                resolvedAuth = future.result(10)
            except FutureTimeout:
                self._json_response({'statusMessage': 'Auth timeout'})
                return
            except Exception as e:
                logger.error(f'Failed to handle auth request callback: {str(e)}')
                self._json_response({'statusMessage': 'Auth error'})
                return
            
            self._json_response({'statusMessage': resolvedAuth[1]})
        else:
            self.send_error(404, "Unknown endpoint")

    def _json_response(self, data):
        response = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

async def start_web(port: int, onResourceAuthCallback: AUTH_CALLBACK_TYPE):
    global _onResourceAuthCallback, _event_loop

    _onResourceAuthCallback = onResourceAuthCallback
    _event_loop = asyncio.get_running_loop()
    handler = BasicHttpHandler
    handler.directory = str(STATIC_FOLDER.parent)

    def runner():
        with socketserver.TCPServer(('0.0.0.0', port), handler) as server:
            logger.info(f'Running on port {port}')
            server.serve_forever()
    
    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
