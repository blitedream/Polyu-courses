# Multi-threaded HTTP Web Server

A simple multi-threaded HTTP/1.0 and HTTP/1.1 web server implemented in Python for the PolyU COMP2322 Computer Networking course.

## Features

- Handles multiple clients concurrently with one thread per connection
- Supports `GET` and `HEAD` requests
- Serves text, HTML, image, and other static files
- Returns `200 OK`, `304 Not Modified`, `400 Bad Request`, `403 Forbidden`, and `404 Not Found`
- Implements cache validation with `Last-Modified` and `If-Modified-Since`
- Supports persistent HTTP/1.1 connections with `keep-alive`
- Prevents access outside the configured web root
- Records requests in `server.log`

## Project structure

```text
HTTP-Web-Server/
├── server.py
└── www/
    ├── index.html
    ├── hello.txt
    └── test.jpg
```

## Run

Requires Python 3. No third-party packages are needed.

```bash
python server.py
```

Open <http://127.0.0.1:8080/> in a browser.

## Test

```bash
# GET
curl http://127.0.0.1:8080/

# HEAD
curl -I http://127.0.0.1:8080/

# 404 Not Found
curl http://127.0.0.1:8080/nonexistent.txt

# 403 Forbidden
curl --path-as-is http://127.0.0.1:8080/../server.py
```

For a `304 Not Modified` test, first copy the response's `Last-Modified` value and send it back in an `If-Modified-Since` header.

```bash
curl -i -H "If-Modified-Since: <Last-Modified value>" http://127.0.0.1:8080/
```

## Public repository note

Course-owned project specifications, personal identifiers, IDE settings, generated logs, and the submitted report are intentionally excluded.
