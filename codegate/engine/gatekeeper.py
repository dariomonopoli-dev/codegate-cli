import http.server
import socketserver
import select
import socket


ALLOWED_DOMAINS = [
    "pypi.org",
    "files.pythonhosted.org",
    "pypi.python.org"
]

class firewall_proxy(http.server.SimpleHTTPRequestHandler):
    def do_CONNECT(self):
        """Handle HTTPS (Secure) Connections"""
        host = self.path.split(":")[0]
        self._audit_traffic(host, is_https=True)

    def do_GET(self):
        """Handle HTTP GET Requests"""
        self._handle_http_method()

    def do_POST(self):
        """Handle HTTP POST Requests (Data Exfiltration)"""
        self._handle_http_method()

    def _handle_http_method(self):
        """Common logic for GET and POST"""

        try:

            host = self.path.split("/")[2]
            if ":" in host:
                host = host.split(":")[0]
            
            self._audit_traffic(host, is_https=False)
        except IndexError:
            self.send_error(400, "Bad Request")

    def _audit_traffic(self, host, is_https=False):
        """Central Logic: Allow List vs Block List"""
        is_allowed = any(domain in host for domain in ALLOWED_DOMAINS)

        if not is_allowed:
            print(f"BLOCKED: Outbound connection to malicious C2: {host}")
            self.send_error(403, "Blocked by CodeGate Runtime Policy")
            return

        print(f"ALLOWED: Traffic to verified PyPI infrastructure: {host}")

        if is_https:
            self._tunnel_traffic(host)
        else:
            self.send_response(200)
            self.end_headers()

    def _tunnel_traffic(self, host):
        try:
            port = 443
            if ":" in self.path:
                port = int(self.path.split(":")[1])

            target_sock = socket.create_connection((host, port))
            self.send_response(200, "Connection Established")
            self.end_headers()

            inputs = [self.connection, target_sock]
            while True:
                readable, _, _ = select.select(inputs, [], [])
                if self.connection in readable:
                    data = self.connection.recv(8192)
                    if not data: break
                    target_sock.sendall(data)
                if target_sock in readable:
                    data = target_sock.recv(8192)
                    if not data: break
                    self.connection.sendall(data)
        except Exception as e:
            pass

def start_gatekeeper(port=8080):
    """Entry point for the CLI to start the firewall"""
    print(f"CodeGate Network Gatekeeper running on port {port}...")
    print(f"Policy: Allow traffic ONLY to {ALLOWED_DOMAINS}")
    
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", port), firewall_proxy) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Gatekeeper stopping...")
            httpd.shutdown()

if __name__ == "__main__":
    start_gatekeeper()