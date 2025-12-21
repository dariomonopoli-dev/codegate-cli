import sqlite3
import requests
import zipfile
import io
import logging
import json
import os
from pathlib import Path
from typing import List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [CRAWLER] - %(message)s', datefmt='%H:%M:%S')

class PyPICrawler:
    def __init__(self):
        """
        Initializes the crawler and sets up the local knowledge graph.
        """
        
        self.app_dir = Path.home() / ".codegate"
        self.app_dir.mkdir(exist_ok=True)
        self.db_path = self.app_dir / "knowledge_graph.db"
        
        self._init_db()
        self._seed_from_json()
        
        self.headers = {
            'User-Agent': 'CodeGate-Security-Indexer/1.0 (runtime-protection-research)'
        }

    def _init_db(self):
        """Ensures the SQLite schema exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS packages (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS provided_imports (package_id INTEGER, import_name TEXT);
                
                -- The "Blocklist" table seeded from your JSON file
                CREATE TABLE IF NOT EXISTS hallucinations (
                    id INTEGER PRIMARY KEY, 
                    name TEXT UNIQUE, 
                    risk_level TEXT, 
                    reason TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_pkg_name ON packages(name);
            """)

    def _seed_from_json(self):
        """
        Loads 'data/hallucinations.json' from the package into SQLite.
        """
        json_path = Path(__file__).parent / "data" / "hallucinations.json"
        
        if not json_path.exists():
            logging.debug(f"No seed file found at {json_path} (Safe to ignore if empty)")
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for entry in data:
                    cursor.execute("""
                        INSERT OR IGNORE INTO hallucinations (name, risk_level, reason)
                        VALUES (?, ?, ?)
                    """, (entry['name'].lower(), entry['risk_level'], entry['reason']))
                conn.commit()
                
        except Exception as e:
            logging.warning(f"Could not seed hallucination DB: {e}")

    def _get_pypi_metadata(self, package_name: str) -> Optional[dict]:
        """Fetch JSON metadata from PyPI."""
        url = f"https://pypi.org/pypi/{package_name}/json"
        try:
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logging.warning(f"Connection error for {package_name}: {e}")
        return None

    def _extract_imports_from_wheel(self, download_url: str) -> List[str]:
        """
        Downloads a wheel file and extracts top-level import names from it.
        """
        try:
            r = requests.get(download_url, headers=self.headers, stream=True)
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for filename in z.namelist():
                    if filename.endswith('top_level.txt'):
                        with z.open(filename) as f:
                            return [line.decode('utf-8').strip() for line in f.readlines() if line.strip()]
        except Exception:
            return []
        return []

    def index_package(self, package_name: str):
        """
        Main entry point to index a single package.
        Checks PyPI, downloads metadata, and saves to local DB.
        """
        package_name = package_name.lower()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM packages WHERE name=?", (package_name,))
            if cursor.fetchone():
                logging.info(f"Skipping {package_name} (Already Indexed)")
                return

            data = self._get_pypi_metadata(package_name)
            if not data:
                logging.warning(f"Package '{package_name}' not found on PyPI.")
                return

            urls = data.get('urls', [])
            wheel_url = next((u['url'] for u in urls if u['packagetype'] == 'bdist_wheel'), None)
            
            found_imports = []
            
            if wheel_url:
                found_imports = self._extract_imports_from_wheel(wheel_url)
            
            if not found_imports:
                found_imports = [package_name.replace('-', '_')]

            cursor.execute("INSERT OR IGNORE INTO packages (name) VALUES (?)", (package_name,))
            pkg_id = cursor.lastrowid
            
            for imp in set(found_imports):
                cursor.execute("INSERT INTO provided_imports (package_id, import_name) VALUES (?, ?)", (pkg_id, imp))
            
            logging.info(f"Indexed '{package_name}' -> provides {found_imports}")