#!/usr/bin/env python3
"""
TCP proxy: bridges Docker containers to host PostgreSQL.

Docker Lambda containers live on the bridge network (172.17.x.x) and cannot
reach host-only services bound to 127.0.0.1.  This proxy listens on all
interfaces (0.0.0.0) so Docker containers can connect via the bridge gateway
(172.17.0.1), and it forwards those connections to the real Postgres on
127.0.0.1:5432.

Usage:  python3 scripts/pg-proxy.py  [proxy_port]  [pg_port]
Called automatically by dev.sh — no need to run it directly.
"""
import socket
import threading
import sys
import os

PROXY_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 15432
PG_HOST = "127.0.0.1"
PG_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5432


def forward(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            src.close()
        except OSError:
            pass
        try:
            dst.close()
        except OSError:
            pass


def handle(client: socket.socket) -> None:
    try:
        server = socket.create_connection((PG_HOST, PG_PORT))
    except OSError as e:
        print(f"  [pg-proxy] Cannot reach {PG_HOST}:{PG_PORT}: {e}", flush=True)
        client.close()
        return

    t1 = threading.Thread(target=forward, args=(client, server), daemon=True)
    t2 = threading.Thread(target=forward, args=(server, client), daemon=True)
    t1.start()
    t2.start()


def main() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PROXY_PORT))
    srv.listen(16)
    print(f"  [pg-proxy] 0.0.0.0:{PROXY_PORT} → {PG_HOST}:{PG_PORT}", flush=True)

    while True:
        try:
            client, _ = srv.accept()
            threading.Thread(target=handle, args=(client,), daemon=True).start()
        except OSError:
            break


if __name__ == "__main__":
    main()
