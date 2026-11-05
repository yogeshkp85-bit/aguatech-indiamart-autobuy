"""
Ultra-lightweight local HTTP/HTTPS CONNECT Proxy for Aguatech Tailscale Routine
Listens on 0.0.0.0:8888 (reachable over Tailscale at 100.99.64.16:8888)
Forwards Google Chrome traffic from Oracle VM out through your local home/office ISP.
"""

import socket
import select
import threading
import sys

# Windows UTF-8 console fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PORT = 8888
BUFFER_SIZE = 32768

def forward(src, dst):
    try:
        while True:
            r, _, _ = select.select([src], [], [], 30)
            if not r:
                break
            data = src.recv(BUFFER_SIZE)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass

def handle_client(client_sock):
    try:
        request = client_sock.recv(BUFFER_SIZE).decode('latin1', errors='ignore')
        if not request:
            client_sock.close()
            return
        
        first_line = request.split('\r\n')[0]
        parts = first_line.split()
        if len(parts) < 3:
            client_sock.close()
            return
        
        method, url, version = parts[0], parts[1], parts[2]

        if method.upper() == 'CONNECT':
            # HTTPS Tunneling
            host, port_str = url.split(':')
            port = int(port_str)
            remote_sock = socket.create_connection((host, port), timeout=10)
            client_sock.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')

            t1 = threading.Thread(target=forward, args=(client_sock, remote_sock), daemon=True)
            t2 = threading.Thread(target=forward, args=(remote_sock, client_sock), daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        else:
            # Plain HTTP
            if url.startswith('http://'):
                url = url[7:]
            path_idx = url.find('/')
            host_port = url if path_idx == -1 else url[:path_idx]
            if ':' in host_port:
                host, port_str = host_port.split(':')
                port = int(port_str)
            else:
                host, port = host_port, 80
            
            remote_sock = socket.create_connection((host, port), timeout=10)
            remote_sock.sendall(request.encode('latin1'))
            forward(remote_sock, client_sock)
    except Exception as e:
        pass
    finally:
        try: client_sock.close()
        except: pass

def start_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(128)
    print(f"[PROXY ACTIVE] Local Indian ISP Proxy active on 0.0.0.0:{PORT} (Tailscale: 100.99.64.16:{PORT})")
    while True:
        client, _ = server.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

if __name__ == '__main__':
    start_proxy()
