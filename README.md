# Minimal HTTP/HTTPS Server

Minimal HTTP/HTTPS Server is an educational HTTP/1.1 server implemented directly on top of Python's low-level TCP socket API. It demonstrates the mechanics normally hidden by web frameworks and production web servers: accepting connections, parsing request lines, constructing responses, serving files, handling concurrent clients, and adding TLS.

The implementation intentionally uses only Python standard library modules. It is designed for study and experimentation rather than production deployment.

## Features

- IPv4 TCP sockets with manual connection handling
- Basic HTTP/1.1 request-line parsing
- Manual status-line, header, and response-body construction
- `GET`, `HEAD`, and `OPTIONS` support
- Static file serving from `www/`
- `200`, `204`, `400`, `404`, and `405` responses
- Thread-per-connection concurrency using daemon threads
- HTTPS/TLS with local files or environment-provided credentials
- Path traversal protection based on normalized absolute paths
- Configurable HTTP port and request debug logging
- Docker image for the custom server
- nginx reference container serving the same page
- ApacheBench performance comparison

## Architecture

```text
Client
  |
  v
TCP Socket
  |
  v
Python HTTP Server
  |
  v
Request Handler (daemon thread)
  |
  +----> Static Files (www/)
  |
  +----> HTTP Response
```

The HTTP and HTTPS listening sockets remain available while each accepted client connection is passed to a separate daemon thread. Each worker receives one request, builds one response, sends it, and closes the client connection.

## Supported HTTP Methods

| Method | Supported | Behavior |
|--------|-----------|----------|
| `GET` | Yes | Serves the requested static resource or the `/slow` demonstration response |
| `HEAD` | Yes | Uses the same lookup as `GET`, but sends headers without a response body |
| `OPTIONS` | Yes | Returns the supported HTTP methods with no response body |

Unsupported methods return:

```http
HTTP/1.1 405 Method Not Allowed
Allow: GET, HEAD, OPTIONS
```

## HTTP Status Codes

| Status | Usage |
|--------|-------|
| `200 OK` | A requested file exists, or the `/slow` endpoint completes |
| `204 No Content` | A valid `OPTIONS` request |
| `400 Bad Request` | The request line cannot be split into exactly three parts |
| `404 Not Found` | The requested file does not exist or the resolved path escapes `www/` |
| `405 Method Not Allowed` | The parsed method is not `GET`, `HEAD`, or `OPTIONS` |

## Configuration

| Setting | Default | Purpose |
|---------|---------|---------|
| `PORT` | `8080` | HTTP listening port |
| `DEBUG` | `1` | Set to `0` to suppress per-request debug output |
| `TLS_CERT` | Unset | PEM certificate content for HTTPS |
| `TLS_KEY` | Unset | PEM private-key content for HTTPS |

Both listeners bind to `0.0.0.0`. HTTPS always uses port `8443` when valid TLS credentials are available.

## Running Locally

The project requires Python 3 and has no external Python dependencies.

```bash
python server.py
```

The default HTTP address is:

```text
http://localhost:8080
```

Set `PORT` before starting the process to use another HTTP port. Set `DEBUG=0` during load tests to disable verbose request logging.

## Testing with curl

GET the default page:

```bash
curl -i http://localhost:8080/
```

Request headers without a response body:

```bash
curl -I http://localhost:8080/
```

Inspect supported methods:

```bash
curl -i -X OPTIONS http://localhost:8080/
```

Send an unsupported method:

```bash
curl -i -X POST http://localhost:8080/
```

Request a missing resource:

```bash
curl -i http://localhost:8080/missing.html
```

## Static Files and Path Handling

The document root is `www/`. A request for `/` maps to `www/index.html`; other paths are resolved relative to the same directory. Query strings are removed before file lookup.

The server normalizes both the document root and requested file path with `os.path.abspath()` and verifies them with `os.path.commonpath()`. Requests such as `../../secret.txt` therefore cannot resolve outside `www/`. This is a focused educational safeguard, not a complete production security layer.

The built-in MIME map covers HTML, CSS, text, PNG, JPEG, and JPG files. Other extensions use `application/octet-stream`.

## HTTPS

When HTTPS is enabled, the server creates an `ssl.SSLContext` in TLS server mode and listens on:

```text
https://localhost:8443
```

TLS credentials are selected in this order:

1. `TLS_CERT` and `TLS_KEY` environment variables. Their PEM contents are written to temporary files, loaded into the SSL context, and the temporary files are removed.
2. Local files at `certs/server.crt` and `certs/server.key`.

Environment variables take precedence over local files. If neither complete credential pair is available, the HTTPS listener is disabled and the HTTP listener continues running. The private key path is excluded by both `.gitignore` and `.dockerignore`.

After a TLS handshake succeeds, the wrapped socket is passed to the same HTTP request handler used for unencrypted connections.

## Docker

Build the custom server image from the repository root:

```bash
docker build -t minimal-http-server .
```

Run it on the default HTTP port:

```bash
docker run --rm -p 8080:8080 minimal-http-server
```

To use another container port, provide the same value through `PORT` and map it on the host:

```bash
docker run --rm -e PORT=9000 -p 9000:9000 minimal-http-server
```

The image is based on `python:3.13-slim` and starts the application with `python server.py`. No framework, reverse proxy, or external Python package is included.

## Benchmark vs nginx

The repository includes an nginx container as a reference static-file server. Both implementations serve the same `index.html` content. The benchmark container uses ApacheBench over private service networking and reads its targets from `CUSTOM_SERVER_URL` and `NGINX_SERVER_URL`.

Each server receives the same static `GET` workload:

- 1,000 requests per run
- Concurrency level of 10
- Three runs per server
- Two-second pause between runs

### Results

| Server | Run 1 req/s | Run 2 req/s | Run 3 req/s | Average req/s | Failed requests |
|--------|-----------:|-----------:|-----------:|--------------:|----------------:|
| Custom Python server | 4567.40 | 4727.62 | 4799.27 | 4698.10 | 0 |
| nginx | 11126.44 | 10178.01 | 12428.07 | 11244.17 | 0 |

nginx achieved approximately **2.39x** the throughput of the custom Python server in this static `GET` experiment. The benchmark script also prints ApacheBench's complete output and summarizes mean time per request and transfer rate for each execution; raw benchmark logs are not stored in the repository.

Build the benchmark image from the repository root:

```bash
docker build -t minimal-http-benchmark ./benchmark
```

Run it with private-network target URLs already exported in the shell:

```bash
docker run --rm \
  -e CUSTOM_SERVER_URL \
  -e NGINX_SERVER_URL \
  minimal-http-benchmark
```

## Why nginx Is Faster

nginx is implemented in C, uses an event-driven architecture, and is extensively optimized for static content and high connection counts. The educational server runs on the Python runtime, creates a thread per connection, and opens and reads static files during request handling. The comparison illustrates architectural trade-offs; matching nginx performance is not the project's objective.

## Project Structure

```text
minimal-http-server/
|-- server.py
|-- Dockerfile
|-- .dockerignore
|-- .gitignore
|-- www/
|   `-- index.html
|-- certs/
|   `-- server.crt
|-- nginx/
|   |-- Dockerfile
|   `-- html/
|       `-- index.html
`-- benchmark/
    |-- Dockerfile
    `-- run_benchmark.sh
```

`certs/server.key` is expected for local file-based TLS but is intentionally excluded from Git and Docker build contexts.

## Limitations

- Parses only the first received chunk, up to 4,096 bytes, and only validates that the request line has three parts
- Supports a deliberately small set of HTTP methods and MIME types
- Handles one request per connection and always returns `Connection: close`
- Uses an unbounded thread-per-connection model rather than a thread pool or event loop
- Reads each static file fully into memory before sending it
- Does not implement persistent connections, chunked transfer encoding, request bodies, range requests, caching, or HTTP/2
- Provides educational TLS support but no automated certificate provisioning or renewal
- Intended for learning and controlled experiments, not production use

## Purpose

The project provides a compact environment for studying TCP sockets, HTTP response semantics, TLS wrapping, concurrent connection handling, container deployment, path validation, and static web-server performance.
