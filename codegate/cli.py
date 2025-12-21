import argparse
import sys
import logging
from pathlib import Path

from codegate.analysis.crawler import PyPICrawler
from codegate.analysis.prober import HallucinationProber
from codegate.analysis.resolver import PackageResolver

try:
    from codegate.engine.orchestrator import run_secure_install
    from codegate.engine.gatekeeper import start_gatekeeper
except ImportError:
    run_secure_install = None
    start_gatekeeper = None

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    parser = argparse.ArgumentParser(description="CodeGate: Zero Trust Supply Chain Firewall")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    install_parser = subparsers.add_parser("install", help="[Runtime] Securely install a package in a sandbox")
    install_parser.add_argument("package", help="Name of the package to install")

    subparsers.add_parser("gatekeeper", help="[Runtime] Start the network firewall proxy")

    analyze_parser = subparsers.add_parser("scan", help="[Static] Scan a requirements.txt file")
    analyze_parser.add_argument("file", help="Path to requirements.txt")

    probe_parser = subparsers.add_parser("probe", help="[Static] Test AI models for hallucinations")
    probe_parser.add_argument("--prompt", help="Custom prompt to test", default=None)

    args = parser.parse_args()

    if args.command == "install":
        if not run_secure_install:
            print("Engine modules not found. Are you running inside the package?")
            sys.exit(1)
        print(f"[CodeGate] Initiating Secure Install for '{args.package}'...")
        run_secure_install(args.package)
    
    elif args.command == "gatekeeper":
        if not start_gatekeeper:
            print("Engine modules not found.")
            sys.exit(1)
        start_gatekeeper()

    elif args.command == "scan":
        crawler = PyPICrawler()
        resolver = PackageResolver(crawler)
        print(f"Scanning '{args.file}' for risky packages...")
        
        try:
            with open(args.file, 'r') as f:
                lines = [line.strip().split('#')[0] for line in f if line.strip()]
            
            for line in lines:
                if not line: continue
                pkg_name = line.split('==')[0].split('>=')[0].split('<')[0].split('~=')[0].strip()
                
                result = resolver.check_package(pkg_name)
                
                if result['status'] == 'BLOCK':
                    print(f"[BLOCK] '{pkg_name}': {result['reason']} (Risk: {result['risk']})")
                elif result['status'] == 'WARN':
                    print(f"[WARN]  '{pkg_name}': {result['reason']}")
                else:
                    print(f"[PASS]  '{pkg_name}'")     
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.")

    elif args.command == "probe":
        crawler = PyPICrawler()
        prober = HallucinationProber(crawler)
        print("Starting hallucination probes...")
        
        prompts = [args.prompt] if args.prompt else [
            "I need a Python library to parse 'X-Financial-98' logs.",
            "How do I interface with 'SoundBlaster 16' drivers in Python?"
        ]
        
        for p in prompts:
            print(f"\n[Prompt] {p}")
            results = prober.probe(p)
            
            if not results:
                print("   (AI suggested no packages)")
            else:
                for res in results:
                    if res['status'] == 'HALLUCINATION':
                        print(f"   DETECTED: {res['package']} (Risk: {res['risk']})")
                    else:
                        print(f"   VERIFIED: {res['package']}")

if __name__ == "__main__":
    main()