"""Tests keeping profiles when upgrading from PySender to Astra Sender."""
import os
import sqlite3
from contextlib import closing
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LegacyMigrationTests(unittest.TestCase):
    def test_imports_old_profile_without_deleting_old_database(self):
        with tempfile.TemporaryDirectory() as root:
            legacy = Path(root) / 'PySender' / 'pysender.db'
            legacy.parent.mkdir()
            with closing(sqlite3.connect(legacy)) as conn, conn:
                conn.execute('CREATE TABLE profiles(id INTEGER PRIMARY KEY, name TEXT NOT NULL)')
                conn.execute("INSERT INTO profiles(name) VALUES ('Antigo WhatsApp')")
            env = dict(os.environ)
            env.pop('ASTRA_SENDER_DATA_DIR', None)
            env.pop('PYSENDER_DATA_DIR', None)
            env['LOCALAPPDATA'] = root
            program = """from app.database import db
 db.initialize_database()
 assert db.one('SELECT name FROM profiles WHERE id=1')['name'] == 'Antigo WhatsApp'
 assert db.DB_PATH.exists()
 """.replace('\n ', '\n')
            r = subprocess.run([sys.executable,'-c',program],cwd=PROJECT_ROOT,env=env,
                               text=True,capture_output=True,timeout=20)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue(legacy.exists())
            self.assertTrue((Path(root)/'AstraSender'/'astra_sender.db').exists())

if __name__ == '__main__':
    unittest.main()
