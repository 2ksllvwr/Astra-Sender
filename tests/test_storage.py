import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Aloca dados em pasta temporaria: nao usa banco real do usuario.
_tmp = tempfile.TemporaryDirectory()
os.environ['PYSENDER_DATA_DIR'] = _tmp.name
from app.database import db


class DatabaseTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        _tmp.cleanup()

    @classmethod
    def setUpClass(cls):
        db.initialize_database()

    def setUp(self):
        with db.connect() as c:
            c.execute('DELETE FROM tasks')
            c.execute('DELETE FROM profiles')
            c.execute('DELETE FROM history')

    def test_profile_saves_with_no_coordinates_and_survives_reconnect(self):
        profile_id = db.save_profile('  Discord ', 'Discord', 'auto', True)
        p = db.one('SELECT * FROM profiles WHERE id=?', (profile_id,))
        self.assertEqual(p['name'], 'Discord')
        self.assertIsNone(p['send_x'])
        db.initialize_database()  # reinicializacao nao apaga registros
        self.assertEqual(db.one('SELECT name FROM profiles WHERE id=?', (profile_id,))['name'], 'Discord')

    def test_window_profile_roundtrip(self):
        pid = db.save_profile('Janela', provider='window', window_process='app.exe',
                              window_title='Chat', editor_hint='Mensagem', chat_url='')
        db.initialize_database()
        p = db.one('SELECT * FROM profiles WHERE id=?', (pid,))
        self.assertEqual(p['window_process'], 'app.exe')
        self.assertEqual(p['window_title'], 'Chat')
        self.assertEqual(p['editor_hint'], 'Mensagem')
        self.assertIsNone(p['send_x'])

    def test_edit_profile_and_save_coordinates_and_message(self):
        profile_id = db.save_profile('Telegram')
        self.assertEqual(db.save_profile('Telegram teste', 'Telegram', 'coords', True, profile_id), profile_id)
        db.set_coordinate(profile_id, 'message', 120, 330)
        db.set_coordinate(profile_id, 'send', 440, 330)
        db.save_draft(profile_id, 'mensagem salva')
        p = db.one('SELECT * FROM profiles WHERE id=?', (profile_id,))
        self.assertEqual((p['message_x'], p['message_y']), (120, 330))
        self.assertEqual((p['send_x'], p['send_y']), (440, 330))
        self.assertEqual(p['default_message'], 'mensagem salva')

    def test_create_task_cancel_and_cascade(self):
        pid = db.save_profile('WhatsApp')
        dt = (datetime.now() + timedelta(hours=1)).isoformat(timespec='seconds')
        task_id = db.create_task(pid, 'Oi', 'write', dt, 'daily')
        self.assertEqual(db.one('SELECT recurrence FROM tasks WHERE id=?', (task_id,))['recurrence'], 'daily')
        db.execute('UPDATE tasks SET status=? WHERE id=?', ('paused', task_id))
        self.assertEqual(db.one('SELECT status FROM tasks WHERE id=?', (task_id,))['status'], 'paused')
        db.delete_profile(pid)
        self.assertIsNone(db.one('SELECT id FROM tasks WHERE id=?', (task_id,)))

    def test_finish_and_record_history(self):
        pid = db.save_profile('Discord')
        tid = db.create_task(pid, 'teste', 'write', datetime.now().isoformat(timespec='seconds'))
        task = db.one('SELECT * FROM tasks WHERE id=?', (tid,))
        db.finish_task(task, result='Acao de teste')
        self.assertEqual(db.one('SELECT status FROM tasks WHERE id=?', (tid,))['status'], 'done')
        self.assertEqual(db.one('SELECT details FROM history ORDER BY id DESC')['details'], 'Acao de teste')

    def test_migrates_old_db_without_default_message(self):
        # O banco de versoes anteriores nao possuia 'default_message'.
        with db.connect() as c:
            c.execute('DROP TABLE profiles')
            c.execute('''CREATE TABLE profiles (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, app_hint TEXT,
                provider TEXT, message_x INTEGER, message_y INTEGER,
                send_x INTEGER, send_y INTEGER, allow_foreground INTEGER)''')
            c.execute('INSERT INTO profiles(id,name) VALUES(8,?)', ('Perfil antigo',))
        db.initialize_database()
        p = db.one('SELECT * FROM profiles WHERE id=8')
        self.assertEqual(p['name'], 'Perfil antigo')
        self.assertEqual(p['default_message'], '')


if __name__ == '__main__':
    unittest.main()
