"""Teste de regressão e smoke test da interface compacta de quatro abas."""
import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'app' / 'ui' / 'main_window.py'


class CompactUiTests(unittest.TestCase):
    def test_qdatetime_uses_supported_date_and_time(self):
        tree = ast.parse(UI.read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
                 isinstance(n.func, ast.Name) and n.func.id == 'QDateTime']
        self.assertGreater(len(calls), 0)
        for n in calls:
            self.assertEqual(len(n.args), 2, f'Argumentos QDateTime inválidos na linha {n.lineno}')
            self.assertEqual(getattr(n.args[0].func, 'id', None), 'QDate')
            self.assertEqual(getattr(n.args[1].func, 'id', None), 'QTime')

    def test_four_top_tabs_and_no_sidebar(self):
        source = UI.read_text(encoding='utf-8')
        for tab in ("'Enviar'", "'Agendamentos'", "'Histórico'", "'Perfis'"):
            self.assertIn('addTab(page, ' + tab, source)
        self.assertNotIn('Macro de mensagens  •  Windows', source)
        self.assertIn("setWindowTitle('Astra Sender')", source)

    @unittest.skipUnless(importlib.util.find_spec('PySide6') is not None,
                         'A instalação de PySide6 é necessária para o teste real da GUI.')
    def test_window_profiles_and_scheduling_dialog_open(self):
        source = '''
from datetime import datetime, timedelta
from PySide6.QtWidgets import QApplication, QDialog
from app.database import db
from app.ui.main_window import MainWindow, ScheduleDialog

db.initialize_database()
app = QApplication([])
pid = db.save_profile('Teste UI')
w = MainWindow()
assert w.windowTitle() == 'Astra Sender'
assert [w.tabs.tabText(i) for i in range(w.tabs.count())] == ['Enviar','Agendamentos','Histórico','Perfis']
assert w.profile.currentData() == pid
assert w.profiles_table.rowCount() == 1
assert w.message.isEnabled()
assert w.coord_label.text().startswith('Campo:')
w.message.setPlainText('Teste de persistência')
w.save_draft()
assert db.one('SELECT default_message FROM profiles WHERE id=?', (pid,))['default_message'] == 'Teste de persistência'
d = ScheduleDialog(w, profile_id=pid, draft='Teste')
assert d.when.dateTime().isValid()
assert d.mode.currentData() == 'write'
t = db.create_task(pid, 'Teste', 'write', (datetime.now() + timedelta(days=1)).isoformat(timespec='seconds'))
d2 = ScheduleDialog(w, task=db.one('SELECT * FROM tasks WHERE id=?', (t,)))
assert d2.when.dateTime().isValid()
w.exiting = True
w.close()
w.executor.shutdown(wait=False)
app.quit()
'''
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env['ASTRA_SENDER_DATA_DIR'] = tmp
            env.pop('PYSENDER_DATA_DIR', None)
            env['QT_QPA_PLATFORM'] = 'offscreen'
            p = subprocess.run([sys.executable, '-c', source], cwd=ROOT, env=env,
                               capture_output=True, text=True, timeout=40)
            self.assertEqual(p.returncode, 0, p.stdout + '\n' + p.stderr)


if __name__ == '__main__':
    unittest.main()
