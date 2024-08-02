import http.server
import json
import os.path
import socket
import socketserver
import threading
import time
import urllib.parse as urlparse

import hub.api.near.sign as near
from nearai.config import load_config_file, save_config_file

# Directory containing the HTML file
DIRECTORY = "nearai/assets"

RECIPIENT = "ai.near"
MESSAGE = "Welcome to NEAR AI"
NONCE = None
PORT = None

httpd = None


def update_auth_config(account_id, signature, public_key, callback_url, nonce):
    if near.verify_signed_message(
            account_id,
            public_key,
            signature,
            MESSAGE,
            nonce,
            RECIPIENT,
            callback_url,
    ):
        config = load_config_file()
        auth = {
            "account_id": account_id,
            "signature": signature,
            "public_key": public_key,
            "callback_url": callback_url,
            "nonce": nonce,
            "recipient": RECIPIENT,
            "message": MESSAGE
        }

        config["auth"] = auth
        save_config_file(config)

        print(f"Auth data been successfully saved! You are now logged in with account ID: {account_id}")
        return True
    else:
        print("Signature verification failed. Abort")
        return False


def print_login_status():
    config = load_config_file()
    if config["auth"].get("account_id"):
        print(f'Auth data for: {config["auth"]["account_id"]}')
        print(f'signature: {config["auth"]["signature"]}')
        print(f'public_key: {config["auth"]["public_key"]}')
        print(f'nonce: {config["auth"]["nonce"]}')
        print(f'message: {config["auth"]["message"]}')
        print(f'recipient: {config["auth"]["recipient"]}')
    else:
        print("Near auth details not found")


class AuthHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Webserver logging method."""
        pass  # Override to suppress logging

    def do_GET(self):  # noqa: N802
        """Webserver GET method."""
        global NONCE, PORT

        if self.path.startswith('/capture'):
            with open(os.path.join(DIRECTORY, "auth_capture.html"), 'r', encoding='utf-8') as file:
                content = file.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))

        if self.path.startswith('/auth'):
            parsed_url = urlparse.urlparse(self.path)
            fragment = parsed_url.query
            params = urlparse.parse_qs(fragment)

            required_params = ['accountId', 'signature', 'publicKey']

            if all(param in params for param in required_params):
                update_auth_config(params['accountId'][0], params['signature'][0], params['publicKey'][0],
                                   callback_url=generate_callback_url(PORT), nonce=NONCE)
            else:
                print("Required parameters not found")

            # http://localhost:50397/auth?accountId=zavodil.near&signature=n5dWHjbywmVYvzNwPCRK5wilamAz50vETrbyZ%2F1P6IjsTpzFz0xPQRtGpx8TcmjQTYT1GfaPXwKnIRvQqPxdAQ%3D%3D&publicKey=ed25519%3AHFd5upW3ppKKqwmNNbm56JW7VHXzEoDpwFKuetXLuNSq&

            with open(os.path.join(DIRECTORY, "auth_complete.html"), 'r', encoding='utf-8') as file:
                content = file.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))

            # Give the server some time to read the response before shutting it down
            def shutdown_server():
                global httpd
                time.sleep(2)  # Wait 2 seconds before shutting down
                if httpd:
                    httpd.shutdown()

            threading.Thread(target=shutdown_server).start()


def find_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def generate_callback_url(port):
    return f"http://localhost:{port}/capture"


def print_url_message(url):
    print(f"Please visit the following URL to complete the login process: {url}")


def generate_nonce():
    return str(int(time.time() * 1000))


def generate_and_save_signature(account_id, private_key):
    nonce = generate_nonce()
    payload = near.Payload(MESSAGE, nonce, RECIPIENT, None)

    signature, public_key = near.create_signature(private_key, payload)

    if update_auth_config(account_id, signature, public_key, None, nonce):
        print_login_status()


def login_with_file_credentials(account_id):
    file_path = os.path.expanduser(os.path.join("~/.near-credentials/", "mainnet", f"{account_id}.json"))

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            content = file.read()
            account_data = json.loads(content)
            private_key = account_data.get("private_key", None)
            if not private_key:
                return print(f"Private key is missing for {account_id} on mainnet")
            generate_and_save_signature(account_id, account_data["private_key"])

    else:
        return print(f"Account data is missing for {account_id}")


def login_with_near_auth(remote, auth_url):
    global NONCE, PORT
    NONCE = generate_nonce()

    params = {
        "message": MESSAGE,
        "nonce": NONCE,
        "recipient": RECIPIENT,

    }

    if not remote:
        PORT = find_open_port()

        global httpd
        with socketserver.TCPServer(("", PORT), AuthHandler) as httpd:
            params["callbackUrl"] = f"http://localhost:{PORT}/capture"

            encoded_params = urlparse.urlencode(params)

            print_url_message(f"{auth_url}?{encoded_params}")

            httpd.serve_forever()

    else:
        encoded_params = urlparse.urlencode(params)

        print_url_message(f"{auth_url}?{encoded_params}")
        print("After visiting the URL, follow the instructions to save your auth signature")
