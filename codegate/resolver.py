import sqlite3
import logging
from pathlib import Path
from typing import Dict

class PackageResolver:
    def __init__(self, crawler):
        self.crawler = crawler
        self.db_path = crawler.db_path

    def check_package(self, package_name: str) -> Dict[str, str]:
        """
        Checks a package. If unknown, it asks the Crawler to fetch it live.
        """
        package_name = package_name.lower()
        
        if not self.db_path.exists():
            return {"status": "WARN", "reason": "DB not initialized", "risk": "unknown"}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT reason, risk_level FROM hallucinations WHERE name=?", (package_name,))
                block_hit = cursor.fetchone()
                if block_hit:
                    return {
                        "status": "BLOCK",
                        "reason": block_hit[0],
                        "risk": block_hit[1]
                    }

                cursor.execute("SELECT id FROM packages WHERE name=?", (package_name,))
                if cursor.fetchone():
                    return {"status": "PASS", "reason": "Verified in Knowledge Graph", "risk": "low"}

            print(f"   (Indexing '{package_name}' from PyPI...)")
            self.crawler.index_package(package_name)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM packages WHERE name=?", (package_name,))
                if cursor.fetchone():
                    return {"status": "PASS", "reason": "Verified on PyPI", "risk": "low"}
                else:
                    return {
                        "status": "WARN", 
                        "reason": "Package does not exist on PyPI (Typo or Hallucination?)", 
                        "risk": "high"
                    }

        except Exception as e:
            logging.error(f"DB Error: {e}")
            return {"status": "WARN", "reason": "Internal Error", "risk": "unknown"}