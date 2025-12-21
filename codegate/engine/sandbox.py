import subprocess
import time
import requests
import os
import json
import platform
import sys

IS_MACOS = platform.system() == "Darwin"

if not IS_MACOS:
    import requests_unixsocket

class FirecrackerSandbox:
    def __init__(self, socket_path="/tmp/firecracker.socket"):
        self.socket_path = socket_path
        self.vm_id = "1"
        self.is_mock = IS_MACOS 
        self.session = None
        
        if not self.is_mock:
            self.session = requests.Session()
            self.session.mount('http+unix://', requests_unixsocket.UnixAdapter())
            self.firecracker_bin = "./firecracker"

    def start_engine(self):
        if self.is_mock:
            time.sleep(0.5) 
            return

        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        cmd = [self.firecracker_bin, "--api-sock", self.socket_path]
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for _ in range(50):
            if os.path.exists(self.socket_path): return
            time.sleep(0.1)
        raise Exception("Firecracker failed to start")

    def configure_vm(self, package_name, proxy_ip="192.168.1.1", proxy_port="8080"):
        install_cmd = (
            f"export http_proxy=http://{proxy_ip}:{proxy_port} && "
            f"export https_proxy=http://{proxy_ip}:{proxy_port} && "
            f"pip install {package_name} --verbose"
        )

        if self.is_mock:
            print(f"   Configuring VM Resources...")
            print(f"   └── Kernel Arg Injection: '{install_cmd}'")
            print(f"   └── Network Tap: tap0 -> Gatekeeper({proxy_ip}:{proxy_port})")
            time.sleep(0.5)
            return

    def start_instance(self):
        if self.is_mock:
            print(f"Booting VM...")
            return
        self._send("PUT", "actions", {"action_type": "InstanceStart"})

    def kill(self):
        if self.is_mock:
            return
        if self.process: self.process.kill()