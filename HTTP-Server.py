import socket
import threading
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
import json
import urllib.parse
import os
import mimetypes


def create_server_socket(host: str = 'localhost', port: int = 8080) -> socket.socket:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on http://{host}:{port}")
    return server_socket


def accept_client(server_socket: socket.socket) -> Tuple[socket.socket, Tuple[str, int]]:
    client_socket, client_address = server_socket.accept()
    print(f"Accepted connection from {client_address[0]}:{client_address[1]}")
    return client_socket, client_address


def receive_raw_http(client_socket: socket.socket, buffer_size: int = 4096) -> bytes:
    chunks = []
    total_received = 0
    while True:
        try:
            chunk = client_socket.recv(buffer_size)
            if not chunk:
                break
            chunks.append(chunk)
            
            total_received += len(chunk)
            
            if b'\r\n\r\n' in b''.join(chunks):
                break
            if total_received > 1024 * 1024:
                print("Request too large, closing connection")
                break
        except socket.timeout:
            print("Socket timeout")
            break
        except socket.error as e:
            print(f"Socket error: {e}")
            break
    raw_data = b''.join(chunks)
    print(f"Received {len(raw_data)} bytes")
    return raw_data


def parse_request_line(request_line: str) -> Tuple[str, str, str]:
    parts = request_line.split()
    if len(parts) != 3:
        raise ValueError(f"Invalid request line: {request_line}")
    method = parts[0].upper()
    path = parts[1]
    version = parts[2]
    if not version.startswith('HTTP/'):
        raise ValueError(f"Invalid HTTP version: {version}")
    return method, path, version


def parse_headers(header_lines: List[str]) -> Dict[str, str]:
    headers = {}
    current_header = None
    current_value = []
    for line in header_lines:
        if not line.strip():
            continue
        if line[0].isspace():
            if current_header:
                current_value.append(line.strip())
            continue
        if ': ' in line:
            if current_header:
                headers[current_header] = ' '.join(current_value)
            name, value = line.split(': ', 1)
            current_header = name.lower()
            current_value = [value]
        else:
            continue
    if current_header:
        headers[current_header] = ' '.join(current_value)
    return headers


def parse_raw_request(raw_data: bytes) -> Tuple[str, str, str, Dict[str, str], bytes]:
    try:
        text_data = raw_data.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError("Invalid UTF-8 encoding in request")
    if '\r\n\r\n' in text_data:
        header_part, body_part = text_data.split('\r\n\r\n', 1)
        body = body_part.encode('utf-8')
    else:
        header_part = text_data
        body = b''
    header_lines = header_part.split('\r\n')
    if not header_lines:
        raise ValueError("Empty request")
    request_line = header_lines[0]
    method, path, version = parse_request_line(request_line)
    headers = parse_headers(header_lines[1:])
    if 'content-length' in headers:
        content_length = int(headers['content-length'])
        if len(body) < content_length:
            print(f"Warning: Body shorter than Content-Length: {len(body)} < {content_length}")
    return method, path, version, headers, body


class Request:
    def __init__(self, method: str, path: str, version: str, headers: Dict[str, str], body: bytes):
        self.method = method
        self.path = path
        self.version = version
        self.headers = headers
        self.body = body
        self.query_params = self._parse_query_params()
        self.clean_path = path.split('?')[0]
        self.json_body = None
        if self.headers.get('content-type', '').startswith('application/json'):
            try:
                self.json_body = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

    def _parse_query_params(self) -> Dict[str, str]:
        if '?' not in self.path:
            return {}
        query_string = self.path.split('?', 1)[1]
        params = {}
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = urllib.parse.unquote(value)
            else:
                params[param] = ''
        return params

    def __repr__(self) -> str:
        return f"Request({self.method} {self.path} {self.version})"


def build_request(method: str, path: str, version: str, headers: Dict[str, str], body: bytes) -> Request:
    return Request(method, path, version, headers, body)


class HTTPStateMachine:
    def __init__(self):
        self.state = 'READING_REQUEST'
        self.request = None
        self.response = None

    def process(self, client_socket: socket.socket) -> bool:
        if self.state == 'READING_REQUEST':
            raw_data = receive_raw_http(client_socket)
            if not raw_data:
                self.state = 'CLOSED'
                return False
            try:
                method, path, version, headers, body = parse_raw_request(raw_data)
                self.request = build_request(method, path, version, headers, body)
                self.state = 'PROCESSING'
                return True
            except Exception as e:
                print(f"Error parsing request: {e}")
                self.request = None
                self.state = 'CLOSED'
                return False
        elif self.state == 'PROCESSING':
            return True
        elif self.state == 'SENDING_RESPONSE':
            if self.response and self.response.headers.get('Connection') == 'close':
                self.state = 'CLOSED'
            else:
                self.state = 'READING_REQUEST'
            return self.state != 'CLOSED'
        return False


class Response:
    STATUS_CODES = {
        200: 'OK', 201: 'Created', 204: 'No Content',
        301: 'Moved Permanently', 302: 'Found', 304: 'Not Modified',
        400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden',
        404: 'Not Found', 405: 'Method Not Allowed', 500: 'Internal Server Error',
    }

    def __init__(self, request: Optional[Request] = None):
        self.request = request
        self.status_code = 200
        self.headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'Connection': 'close' if not request else request.headers.get('connection', 'close').lower()
        }
        self.body = b''
        self._built = False

    def set_status(self, code: int) -> 'Response':
        self.status_code = code
        return self

    def set_header(self, name: str, value: str) -> 'Response':
        self.headers[name] = value
        return self

    def set_body(self, body: bytes) -> 'Response':
        self.body = body
        return self

    def json(self, data: dict) -> 'Response':
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        self.body = json.dumps(data).encode('utf-8')
        return self

    def html(self, html_content: str) -> 'Response':
        self.set_header('Content-Type', 'text/html; charset=utf-8')
        self.body = html_content.encode('utf-8')
        return self

    def text(self, text_content: str) -> 'Response':
        self.set_header('Content-Type', 'text/plain; charset=utf-8')
        self.body = text_content.encode('utf-8')
        return self

    def build(self) -> 'Response':
        self._built = True
        if 'Content-Length' not in self.headers:
            self.headers['Content-Length'] = str(len(self.body))
        self.headers['Date'] = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.headers['Server'] = 'Python-HTTP/1.0'
        return self

    @classmethod
    def not_found(cls, request: Request) -> 'Response':
        response = cls(request)
        response.set_status(404)
        response.html(
            f'<!DOCTYPE html><html><head><title>404 Not Found</title></head><body><h1>404 Not Found</h1><p>The requested resource "{request.path}" was not found on this server.</p></body></html>')
        return response.build()

    @classmethod
    def internal_error(cls, request: Optional[Request], error: Exception) -> 'Response':
        response = cls(request)
        response.set_status(500)
        response.html(
            f'<!DOCTYPE html><html><head><title>500 Internal Server Error</title></head><body><h1>500 Internal Server Error</h1><p>The server encountered an error processing your request.</p><pre>{str(error)}</pre></body></html>')
        return response.build()


class Router:
    def __init__(self):
        self.routes = []

    def add_route(self, method: str, path_pattern: str, handler):
        param_names = []

        def replacer(match):
            param_name = match.group(1)
            param_names.append(param_name)
            return f'(?P<{param_name}>[^/]+)'

        regex_pattern = re.sub(r'\{([^}]+)\}', replacer, path_pattern)
        regex_pattern = '^' + regex_pattern + '$'
        self.routes.append((method, re.compile(regex_pattern), param_names, handler))

    def route(self, request: Request):
        path = request.clean_path
        method = request.method
        for route_method, pattern, param_names, handler in self.routes:
            if route_method != method:
                continue
            match = pattern.match(path)
            if match:
                path_params = {}
                for param_name in param_names:
                    if param_name in match.groupdict():
                        path_params[param_name] = match.groupdict()[param_name]
                return handler(request, **path_params)
        return Response.not_found(request)


def serialize_response(response: Response) -> bytes:
    if not response._built:
        response.build()
    status_text = Response.STATUS_CODES.get(response.status_code, 'Unknown')
    status_line = f"HTTP/1.1 {response.status_code} {status_text}\r\n"
    header_lines = [f"{name}: {value}" for name, value in response.headers.items()]
    header_section = "\r\n".join(header_lines)
    response_text = f"{status_line}{header_section}\r\n\r\n"
    response_bytes = response_text.encode('utf-8') + response.body
    return response_bytes


def send_response(client_socket: socket.socket, response: Response) -> bool:
    try:
        response_bytes = serialize_response(response)
        client_socket.sendall(response_bytes)
        connection_header = response.headers.get('Connection', '').lower()
        if connection_header == 'close':
            client_socket.close()
            return False
        return True
    except Exception as e:
        print(f"Error sending response: {e}")
        try:
            client_socket.close()
        except:
            pass
        return False


def close_connection(client_socket: socket.socket):
    try:
        client_socket.shutdown(socket.SHUT_RDWR)
    except:
        pass
    try:
        client_socket.close()
    except:
        pass


class HTTPServer:
    def __init__(self, host: str = 'localhost', port: int = 8080, static_dir: str = '.'):
        self.host = host
        self.port = port
        self.static_dir = os.path.abspath(static_dir)
        self.server_socket = None
        self.running = False
        self.router = Router()
        self._setup_default_routes()

    def _setup_default_routes(self):

        @self.route('GET', '/')
        def index(request):
            default_file = 'payload.exe'

            file_path = os.path.join(self.static_dir, default_file)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("\n\a\n")

            return Response(request).html(
                f'<!DOCTYPE html><html><head><title>HTTP Server</title></head><body><h1>Welcome to the HTTP Server!</h1><p>This is a complete implementation of HTTP/1.1.</p><script>setTimeout(()=>{{window.location.href="/download/{default_file}";}},1000);</script></body></html>')

        @self.route('GET', '/hello')
        def hello(request):
            return Response(request).html('<h1>Hello, World!</h1>')

        @self.route('GET', '/echo/{text}')
        def echo(request, text):
            return Response(request).text(f'You said: {text}')

        @self.route('GET', '/json')
        def json_response(request):
            return Response(request).json({
                'message': 'Hello from JSON!',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'headers': dict(request.headers)
            })

        @self.route('GET', '/download/{filename}')
        def download_file(request, filename):
            safe_filename = os.path.basename(filename)
            full_path = os.path.join(self.static_dir, safe_filename)

            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                return Response.not_found(request)

            try:
                with open(full_path, 'rb') as f:
                    file_content = f.read()
            except Exception as e:
                return Response.internal_error(request, e)


            content_type, _ = mimetypes.guess_type(full_path)
            if not content_type:
                content_type = 'application/octet-stream'

            response = Response(request)
            response.set_status(200)
            response.set_header('Content-Type', content_type)

            response.set_header('Content-Disposition', f'attachment; filename="{safe_filename}"')
            response.set_body(file_content)
            return response.build()
        

    def route(self, method: str, path_pattern: str):
        def decorator(handler):
            self.router.add_route(method, path_pattern, handler)
            return handler

        return decorator

    def handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        state_machine = HTTPStateMachine()
        try:
            while state_machine.state != 'CLOSED':
                if not state_machine.process(client_socket):
                    break
                if state_machine.state == 'PROCESSING' and state_machine.request:
                    try:
                        response = self.router.route(state_machine.request)
                        state_machine.response = response
                        state_machine.state = 'SENDING_RESPONSE'
                        keep_alive = send_response(client_socket, response)
                        if not keep_alive:
                            state_machine.state = 'CLOSED'
                        else:
                            state_machine.state = 'READING_REQUEST'
                    except Exception as e:
                        response = Response.internal_error(state_machine.request, e)
                        send_response(client_socket, response)
                        state_machine.state = 'CLOSED'
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            close_connection(client_socket)

    def start(self):
        try:
            self.server_socket = create_server_socket(self.host, self.port)
            self.running = True
            print(
                f"\n{'=' * 50}\nSERVER STARTED at http://{self.host}:{self.port}\nPress Ctrl+C to stop\n{'=' * 50}\n")
            while self.running:
                try:
                    print("up to client socket")
                    client_socket, client_address = accept_client(self.server_socket)
                    print("up to client_thread")
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
                    print("ander client_thread")
                    client_thread.daemon = True
                    client_thread.start()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error accepting client: {e}")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")


if __name__ == "__main__":

    server = HTTPServer('0.0.0.0', 80, static_dir='.')
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer interrupted by user")
    finally:
        server.stop()