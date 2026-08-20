import socket
import threading
import os
from email.utils import formatdate, parsedate_to_datetime

HOST = "127.0.0.1"
PORT = 8080

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.join(CURRENT_DIR, "www")
LOG_FILE = os.path.join(CURRENT_DIR, "server.log")

log_lock = threading.Lock()


def get_content_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".html" or ext == ".htm":
        return "text/html; charset=utf-8"
    elif ext == ".txt":
        return "text/plain; charset=utf-8"
    elif ext == ".jpg" or ext == ".jpeg":
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".gif":
        return "image/gif"
    else:
        return "application/octet-stream"


def build_response(status_line, content_type, body_bytes, connection_value, extra_headers=None):
    header = (
        f"{status_line}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: {connection_value}\r\n"
    )

    if extra_headers:
        for k, v in extra_headers.items():
            header += f"{k}: {v}\r\n"

    header += "\r\n"

    return header.encode("iso-8859-1") + body_bytes


def build_header(status_line, content_type, content_length, connection_value, extra_headers=None):
    header = (
        f"{status_line}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {content_length}\r\n"
        f"Connection: {connection_value}\r\n"
    )

    if extra_headers:
        for k, v in extra_headers.items():
            header += f"{k}: {v}\r\n"

    header += "\r\n"
    return header.encode("iso-8859-1")


def write_log(client_address, path, status_code):
    log_line = f"{client_address[0]} [{formatdate(usegmt=True)}] {path} {status_code}\n"

    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)


def handle_client(client_socket, client_address):
    try:
        print(f"[NEW CONNECTION] {client_address}")

        while True:
            request_data = b""

            while b"\r\n\r\n" not in request_data:
                chunk = client_socket.recv(4096)
                if not chunk:
                    return
                request_data += chunk

                if len(request_data) > 65536:
                    break

            if not request_data:
                return

            request_text = request_data.decode("iso-8859-1")

            print("REQUEST START")
            print(request_text)
            print("REQUEST END")

            lines = request_text.split("\r\n")

            if len(lines) == 0 or lines[0] == "":
                body = b"<h1>400 Bad Request</h1>"
                response = build_response(
                    "HTTP/1.1 400 Bad Request",
                    "text/html; charset=utf-8",
                    body,
                    "close"
                )
                client_socket.sendall(response)
                write_log(client_address, "-", "400")
                return

            request_line = lines[0]
            parts = request_line.split()

            if len(parts) != 3:
                body = b"<h1>400 Bad Request</h1>"
                response = build_response(
                    "HTTP/1.1 400 Bad Request",
                    "text/html; charset=utf-8",
                    body,
                    "close"
                )
                client_socket.sendall(response)
                write_log(client_address, "-", "400")
                return

            method, path, version = parts

            headers = {}
            for line in lines[1:]:
                if line == "":
                    break
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key] = value

            connection_header = headers.get("Connection", "keep-alive").lower()

            if connection_header == "close":
                connection_value = "close"
                keep_alive = False
            else:
                connection_value = "keep-alive"
                keep_alive = True

            if version not in ["HTTP/1.0", "HTTP/1.1"]:
                body = b"<h1>400 Bad Request</h1>"
                response = build_response(
                    "HTTP/1.1 400 Bad Request",
                    "text/html; charset=utf-8",
                    body,
                    connection_value
                )
                client_socket.sendall(response)
                write_log(client_address, path, "400")
                if not keep_alive:
                    return
                continue

            if method != "GET" and method != "HEAD":
                body = b"<h1>400 Bad Request</h1>"
                response = build_response(
                    "HTTP/1.1 400 Bad Request",
                    "text/html; charset=utf-8",
                    body,
                    connection_value
                )
                client_socket.sendall(response)
                write_log(client_address, path, "400")
                if not keep_alive:
                    return
                continue

            if path == "/":
                path = "/index.html"

            safe_path = path.lstrip("/")
            file_path = os.path.join(WEB_ROOT, safe_path)

            real_root = os.path.realpath(WEB_ROOT)
            real_path = os.path.realpath(file_path)

            if os.path.commonpath([real_root, real_path]) != real_root:
                body = b"<h1>403 Forbidden</h1>"
                response = build_response(
                    "HTTP/1.1 403 Forbidden",
                    "text/html; charset=utf-8",
                    body,
                    connection_value
                )
                client_socket.sendall(response)
                write_log(client_address, path, "403")
                if not keep_alive:
                    return
                continue

            if not os.path.isfile(real_path):
                body = b"<h1>404 File Not Found</h1>"
                response = build_response(
                    "HTTP/1.1 404 Not Found",
                    "text/html; charset=utf-8",
                    body,
                    connection_value
                )
                client_socket.sendall(response)
                write_log(client_address, path, "404")
                if not keep_alive:
                    return
                continue

            last_modified_time = os.path.getmtime(real_path)
            last_modified_str = formatdate(last_modified_time, usegmt=True)

            if_modified_since = headers.get("If-Modified-Since")

            if if_modified_since:
                try:
                    client_time = parsedate_to_datetime(if_modified_since)
                    server_time = parsedate_to_datetime(last_modified_str)

                    if server_time <= client_time:
                        header = build_header(
                            "HTTP/1.1 304 Not Modified",
                            get_content_type(real_path),
                            0,
                            connection_value,
                            {"Last-Modified": last_modified_str}
                        )
                        client_socket.sendall(header)
                        write_log(client_address, path, "304")
                        if not keep_alive:
                            return
                        continue
                except:
                    pass

            with open(real_path, "rb") as f:
                body_bytes = f.read()

            content_type = get_content_type(real_path)
            content_length = len(body_bytes)

            extra_headers = {
                "Last-Modified": last_modified_str
            }

            if method == "GET":
                response = build_response(
                    "HTTP/1.1 200 OK",
                    content_type,
                    body_bytes,
                    connection_value,
                    extra_headers
                )
                client_socket.sendall(response)
                write_log(client_address, path, "200")

            elif method == "HEAD":
                header = build_header(
                    "HTTP/1.1 200 OK",
                    content_type,
                    content_length,
                    connection_value,
                    extra_headers
                )
                client_socket.sendall(header)
                write_log(client_address, path, "200")

            if not keep_alive:
                return

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        client_socket.close()
        print(f"[CLOSED] {client_address}")


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    print(f"Server running on http://{HOST}:{PORT}")
    print(f"WEB_ROOT = {WEB_ROOT}")

    while True:
        client_socket, client_address = server_socket.accept()

        thread = threading.Thread(
            target=handle_client,
            args=(client_socket, client_address)
        )
        thread.start()


if __name__ == "__main__":
    main()