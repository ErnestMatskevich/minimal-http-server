import os
import socket
import ssl
import tempfile
import threading
import time


HOST = "0.0.0.0"
HTTP_PORT = int(os.environ.get("PORT", "8080"))
HTTPS_PORT = 8443
BUFFER_SIZE = 4096
DEBUG = os.environ.get("DEBUG", "1") != "0"
DOCUMENT_ROOT = os.path.abspath("www")
CERT_FILE = os.path.join("certs", "server.crt")
KEY_FILE = os.path.join("certs", "server.key")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def handle_client(client_socket, client_address):
    with client_socket:
        client_ip, client_port = client_address
        thread_name = threading.current_thread().name
        if DEBUG:
            print(f"Client connected from {client_ip}:{client_port} on {thread_name}")

        data = client_socket.recv(BUFFER_SIZE)
        request_text = data.decode("utf-8", errors="replace")

        if DEBUG:
            print("Received data:")
            print(request_text)

        request_line = request_text.splitlines()[0] if request_text else ""
        request_parts = request_line.split()

        if len(request_parts) == 3:
            method, path, version = request_parts

            if DEBUG:
                print(f"Method: {method}")
                print(f"Path: {path}")
                print(f"Version: {version}")
                print(f"[{thread_name}] {client_ip}:{client_port} {method} {path}")

            if method != "GET":
                status_line = "HTTP/1.1 405 Method Not Allowed"
                content_type = "text/plain; charset=utf-8"
                body = "405 Method Not Allowed".encode("utf-8")
            else:
                url_path = path.split("?", 1)[0]

                if url_path == "/slow":
                    if DEBUG:
                        print(f"[{thread_name}] Slow processing started")
                    time.sleep(5)
                    status_line = "HTTP/1.1 200 OK"
                    content_type = "text/plain; charset=utf-8"
                    body = "Slow request completed".encode("utf-8")
                else:
                    relative_path = "index.html" if url_path == "/" else url_path.lstrip("/")
                    file_path = os.path.abspath(os.path.join(DOCUMENT_ROOT, relative_path))

                    if os.path.commonpath([DOCUMENT_ROOT, file_path]) != DOCUMENT_ROOT:
                        status_line = "HTTP/1.1 404 Not Found"
                        content_type = "text/plain; charset=utf-8"
                        body = "404 Not Found".encode("utf-8")
                    elif os.path.isfile(file_path):
                        extension = os.path.splitext(file_path)[1].lower()
                        content_type = CONTENT_TYPES.get(extension, "application/octet-stream")

                        with open(file_path, "rb") as file:
                            body = file.read()

                        status_line = "HTTP/1.1 200 OK"
                    else:
                        status_line = "HTTP/1.1 404 Not Found"
                        content_type = "text/plain; charset=utf-8"
                        body = "404 Not Found".encode("utf-8")
        else:
            status_line = "HTTP/1.1 400 Bad Request"
            content_type = "text/plain; charset=utf-8"
            body = "Bad Request".encode("utf-8")

        response = (
            f"{status_line}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8") + body

        client_socket.sendall(response)


def serve_http():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, HTTP_PORT))
        server_socket.listen()

        print(f"HTTP listening on {HOST}:{HTTP_PORT}", flush=True)

        while True:
            client_socket, client_address = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                daemon=True,
            )
            client_thread.start()


def serve_https(ssl_context):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, HTTPS_PORT))
        server_socket.listen()

        print(f"HTTPS listening on {HOST}:{HTTPS_PORT}", flush=True)

        while True:
            client_socket, client_address = server_socket.accept()

            try:
                tls_socket = ssl_context.wrap_socket(client_socket, server_side=True)
            except ssl.SSLError as error:
                print(f"TLS handshake failed from {client_address}: {error}")
                client_socket.close()
                continue

            client_thread = threading.Thread(
                target=handle_client,
                args=(tls_socket, client_address),
                daemon=True,
            )
            client_thread.start()


def create_ssl_context():
    tls_cert = os.environ.get("TLS_CERT")
    tls_key = os.environ.get("TLS_KEY")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    if tls_cert and tls_key:
        cert_path = None
        key_path = None

        try:
            with tempfile.NamedTemporaryFile("w", delete=False) as cert_file:
                cert_file.write(tls_cert.replace("\\n", "\n"))
                cert_path = cert_file.name

            with tempfile.NamedTemporaryFile("w", delete=False) as key_file:
                key_file.write(tls_key.replace("\\n", "\n"))
                key_path = key_file.name

            context.load_cert_chain(certfile=cert_path, keyfile=key_path)
            print("HTTPS enabled using TLS_CERT and TLS_KEY environment variables", flush=True)
            return context
        finally:
            if cert_path:
                os.remove(cert_path)
            if key_path:
                os.remove(key_path)

    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
        print(f"HTTPS enabled using {CERT_FILE} and {KEY_FILE}", flush=True)
        return context

    print("HTTPS disabled: missing TLS_CERT/TLS_KEY and local certificate files", flush=True)
    return None


http_thread = threading.Thread(target=serve_http, daemon=True)
http_thread.start()

context = create_ssl_context()
if context:
    https_thread = threading.Thread(target=serve_https, args=(context,), daemon=True)
    https_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nServer stopped.")
