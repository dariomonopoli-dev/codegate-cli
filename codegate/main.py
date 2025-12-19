import sys
import argparse
import logging
from codegate.crawler import PyPICrawler
from codegate.prober import HallucinationProber
from codegate.resolver import PackageResolver

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    parser = argparse.ArgumentParser(description="CodeGate CLI: Supply Chain Defense")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan
    analyze_parser = subparsers.add_parser("scan", help="Scan a requirements.txt file")
    analyze_parser.add_argument("file", help="Path to requirements.txt")

    # probe
    probe_parser = subparsers.add_parser("probe", help="Test AI models for hallucinations")
    probe_parser.add_argument("--prompt", help="Custom prompt to test", default=None)
    
    args = parser.parse_args()
    

    crawler = PyPICrawler()

    resolver = PackageResolver(crawler)

    if args.command == "scan":
        print(f"scanning '{args.file}' for risky packages...")
        try:
            with open(args.file, 'r') as f:
                lines = [line.strip().split('#')[0] for line in f if line.strip()]
            
            for line in lines:
                if not line: continue

                pkg_name = line.split('==')[0].split('>=')[0].split('<')[0].split('~=')[0].strip()
                

                result = resolver.check_package(pkg_name)
                
                if result['status'] == 'BLOCK':
                    print(f"🚨 [BLOCK] '{pkg_name}': {result['reason']} (Risk: {result['risk']})")
                elif result['status'] == 'WARN':
                    print(f"⚠️  [WARN]  '{pkg_name}': {result['reason']}")
                else:
                    print(f"✅ [PASS]  '{pkg_name}'")
                        
        except FileNotFoundError:
            print(f"error: File '{args.file}' not found.")

    elif args.command == "probe":
        print("starting hallucination probes...")
        prober = HallucinationProber(crawler)
        
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
                        print(f"   🚨 DETECTED: {res['package']} (Risk: {res['risk']})")
                    else:
                        print(f"   ✅ VERIFIED: {res['package']}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()