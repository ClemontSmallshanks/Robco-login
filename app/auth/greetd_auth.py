"""greetd IPC authenticator implementation."""

import os
import json
import socket
import struct
from typing import Optional

from app.auth.authenticator import Authenticator


class GreetdAuthenticator(Authenticator):
    """Authenticates using greetd's JSON IPC protocol over a Unix socket."""

    def __init__(self) -> None:
        self.sock_path = os.environ.get("GREETD_SOCK")
        
    def _send_request(self, sock: socket.socket, payload: dict) -> dict:
        """Send a JSON payload and receive the response."""
        data = json.dumps(payload).encode("utf-8")
        # greetd IPC uses a 32-bit little-endian length prefix
        header = struct.pack("<I", len(data))
        sock.sendall(header + data)

        # Read the 4-byte header
        resp_header = sock.recv(4)
        if len(resp_header) != 4:
            raise RuntimeError("Failed to read greetd IPC header")
        
        resp_len = struct.unpack("<I", resp_header)[0]
        
        # Read the payload
        resp_data = b""
        while len(resp_data) < resp_len:
            chunk = sock.recv(resp_len - len(resp_data))
            if not chunk:
                raise RuntimeError("greetd socket closed unexpectedly")
            resp_data += chunk
            
        return json.loads(resp_data.decode("utf-8"))

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with greetd.
        
        If successful, it will immediately instruct greetd to start the KDE Wayland session.
        This function will not return True; it will exit the greeter process as greetd takes over.
        It returns False if authentication fails.
        """
        if not self.sock_path or not os.path.exists(self.sock_path):
            print("ERROR: GREETD_SOCK not set or invalid. Are you running under greetd?")
            return False

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(self.sock_path)
                
                # 1. Create the session for the user
                resp = self._send_request(sock, {
                    "type": "create_session",
                    "username": username
                })
                
                # greetd PAM loop
                while resp.get("type") == "auth_message":
                    msg_type = resp.get("auth_message_type")
                    
                    if msg_type in ("secret", "visible"):
                        # Send the password when prompted for a secret/visible input
                        resp = self._send_request(sock, {
                            "type": "post_auth_message_response",
                            "response": password
                        })
                    elif msg_type in ("info", "error"):
                        # Just acknowledge informational messages with an empty string
                        resp = self._send_request(sock, {
                            "type": "post_auth_message_response",
                            "response": ""
                        })
                    else:
                        print(f"Unknown greetd auth_message_type: {msg_type}")
                        return False
                
                # 2. Check if authentication was successful
                if resp.get("type") == "success":
                    # Authentication succeeded! Tell greetd to start the session.
                    # This will tear down the greeter (cage) and launch the user's session.
                    self._send_request(sock, {
                        "type": "start_session",
                        "cmd": ["startplasma-wayland"]
                    })
                    # We should not reach here as the session starts, but if we do, return True.
                    return True
                    
                elif resp.get("type") == "error":
                    error_type = resp.get("error_type", "unknown")
                    error_desc = resp.get("description", "No description")
                    print(f"greetd authentication error: {error_type} - {error_desc}")
                    return False
                
                print(f"Unexpected greetd response: {resp}")
                return False
                
        except Exception as e:
            print(f"greetd IPC error: {e}")
            return False

    def get_available_users(self) -> list[str]:
        # Typically you'd read /etc/passwd filtering for UID >= 1000
        # For this implementation, we can just return a placeholder or scan passwd.
        users = []
        try:
            with open("/etc/passwd", "r") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 3:
                        uid = int(parts[2])
                        if 1000 <= uid < 60000:
                            users.append(parts[0])
        except Exception:
            pass
        return users
