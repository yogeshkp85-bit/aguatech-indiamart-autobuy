#!/usr/bin/env python3
"""
Aguatech IndiaMART Auto-Failover Proxy Dispatcher
Runs locally on Oracle Cloud VM (127.0.0.1:8888).

Route Logic:
1. PRIMARY: Office Laptop Proxy (100.99.64.16:8888) when laptop is ON / awake.
2. SECONDARY: iPhone Exit Node (100.108.84.37) when laptop is OFF / sleeping.
"""

import socket
import select
import threading
import time
import subprocess
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [FailoverProxy] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("FailoverProxy")

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8888

LAPTOP_IP = "100.99.64.16"
LAPTOP_PORT = 8888
IPHONE_IP = "100.108.84.37"

# State
active_gateway = "PRIMARY_LAPTOP"
laptop_is_alive = True
lock = threading.Lock()

def check_laptop_port():
    """Check if laptop proxy port 8888 is reachable within 1.5s"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect((LAPTOP_IP, LAPTOP_PORT))
        s.close()
        return True
    except Exception:
        return False

def ensure_tailscale_exit_node(exit_ip):
    """Ensure Tailscale exit node preference is set"""
    try:
        cmd = ["sudo", "tailscale", "set", f"--exit-node={exit_ip}", "--exit-node-allow-lan-access=true"]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.error(f"Failed to set exit node {exit_ip}: {e}")

def health_check_loop():
    global active_gateway, laptop_is_alive
    logger.info("Health check thread started. Monitoring Laptop and iPhone...")
    
    # Start with iPhone exit node active as backup route baseline
    ensure_tailscale_exit_node(IPHONE_IP)
    
    while True:
        alive = check_laptop_port()
        with lock:
            if alive and not laptop_is_alive:
                logger.info("🟢 Laptop (desktop-udgq40p) is ONLINE! Switching to Laptop Proxy.")
                active_gateway = "PRIMARY_LAPTOP"
                laptop_is_alive = True
            elif not alive and laptop_is_alive:
                logger.warning("🟡 Laptop is OFFLINE / Closed! Switching to iPhone (yogeshs-iphone-95th).")
                active_gateway = "SECONDARY_IPHONE"
                laptop_is_alive = False
                ensure_tailscale_exit_node(IPHONE_IP)
        time.sleep(3)

def pipe_sockets(s1, s2):
    """Bidirectional forward between two sockets"""
    try:
        while True:
            r, _, x = select.select([s1, s2], [], [s1, s2], 60)
            if x:
                break
            if not r:
                break
            for s in r:
                data = s.recv(65536)
                if not data:
                    return
                other = s2 if s is s1 else s1
                other.sendall(data)
    except Exception:
        pass
    finally:
        try: s1.close()
        except: pass
        try: s2.close()
        except: pass

def handle_client(client_sock):
    client_sock.settimeout(10.0)
    try:
        request_line = b""
        while b"\r\n" not in request_line and len(request_line) < 4096:
            chunk = client_sock.recv(1)
            if not chunk:
                client_sock.close()
                return
            request_line += chunk

        parts = request_line.decode('utf-8', errors='ignore').strip().split()
        if not parts:
            client_sock.close()
            return
        
        method = parts[0]
        target = parts[1] if len(parts) > 1 else ""

        # Drain rest of client headers
        headers = request_line
        while b"\r\n\r\n" not in headers and len(headers) < 65536:
            chunk = client_sock.recv(1024)
            if not chunk:
                break
            headers += chunk

        with lock:
            current_route = active_gateway

        if current_route == "PRIMARY_LAPTOP":
            # Forward directly to Laptop proxy
            upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            upstream.settimeout(5.0)
            try:
                upstream.connect((LAPTOP_IP, LAPTOP_PORT))
                upstream.sendall(headers)
                client_sock.settimeout(None)
                upstream.settimeout(None)
                pipe_sockets(client_sock, upstream)
                return
            except Exception as e:
                logger.warning(f"Failed to connect to laptop proxy: {e}. Falling back to iPhone direct.")
                upstream.close()

        # SECONDARY: Route directly via host IP (exit node routes through iPhone)
        if method.upper() == "CONNECT":
            # Target is host:port
            if ":" in target:
                host, port = target.split(":", 1)
                port = int(port)
            else:
                host = target
                port = 443
            
            upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            upstream.settimeout(10.0)
            try:
                upstream.connect((host, port))
                client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                client_sock.settimeout(None)
                upstream.settimeout(None)
                pipe_sockets(client_sock, upstream)
            except Exception as e:
                client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                client_sock.close()
        else:
            # Plain HTTP request
            # Target is http://host:port/path or /path
            if target.startswith("http://"):
                url_part = target[7:]
                host_part = url_part.split("/")[0]
                if ":" in host_part:
                    host, port = host_part.split(":", 1)
                    port = int(port)
                else:
                    host = host_part
                    port = 80
            else:
                host = "127.0.0.1"
                port = 80

            upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            upstream.settimeout(10.0)
            try:
                upstream.connect((host, port))
                upstream.sendall(headers)
                client_sock.settimeout(None)
                upstream.settimeout(None)
                pipe_sockets(client_sock, upstream)
            except Exception:
                client_sock.close()

    except Exception:
        try: client_sock.close()
        except: pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(128)

    t = threading.Thread(target=health_check_loop, daemon=True)
    t.start()

    logger.info(f"⚡ Failover Proxy listening on http://{LISTEN_HOST}:{LISTEN_PORT}")
    logger.info(f"   Primary Gateway:   Laptop at http://{LAPTOP_IP}:{LAPTOP_PORT}")
    logger.info(f"   Secondary Gateway: iPhone Exit Node at {IPHONE_IP}")

    while True:
        try:
            client_sock, _ = server.accept()
            th = threading.Thread(target=handle_client, args=(client_sock,), daemon=True)
            th.start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Accept error: {e}")

if __name__ == "__main__":
    main()
