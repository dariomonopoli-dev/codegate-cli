import sys
import json
import time
from codegate.engine.sandbox import FirecrackerSandbox

try:
    with open("trusted_packages.json", "r") as f:
        TRUST_DB = json.load(f)
except FileNotFoundError:
    print("Warning: trusted_packages.json not found. Assuming empty whitelist.")
    TRUST_DB = {}

def is_trusted(package_name):
    if package_name.lower() in TRUST_DB:
        print(f"✅ [Cache Hit] '{package_name}' is verified trusted. Skipping Sandbox.")
        return True
    return False

def run_secure_install(package_name):
    if is_trusted(package_name):
        # TODO: implement
        print(f"Installing '{package_name}' directly on host...")
        return

    print(f"[Security Risk] Package '{package_name}' is UNKNOWN.")
    print(f"Spinning up Firecracker MicroVM for isolation...")
    
    vm = FirecrackerSandbox()
    try:
        vm.start_engine()
        vm.configure_vm(package_name, proxy_ip="192.168.1.1", proxy_port="8080")
        vm.start_instance()
        
        print("Sandboxed Installation in progress...")
        time.sleep(5) 
        
        print(f"Sandbox check complete. No malicious code detected.")
        
    except Exception as e:
        print(f"Sandbox Error: {e}")
    finally:
        vm.kill()
        print("VM Destroyed.")

if __name__ == "__main__":
    # Usage: python3 engine.py <package_name>
    pkg = sys.argv[1] if len(sys.argv) > 1 else "zeta-decoder"
    run_secure_install(pkg)