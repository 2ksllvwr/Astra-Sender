"""Astra Sender: SQLite por usuário, com migração e transações explícitas."""
import os
import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path
from datetime import datetime, timedelta

USER_DATA = Path(os.getenv('LOCALAPPDATA') or (Path.home() / '.local' / 'share'))
CUSTOM_DATA_DIR = os.getenv('ASTRA_SENDER_DATA_DIR') or os.getenv('PYSENDER_DATA_DIR')
ROOT = Path(CUSTOM_DATA_DIR) if CUSTOM_DATA_DIR else (USER_DATA / 'AstraSender')
DB_PATH = ROOT / 'astra_sender.db'
LEGACY_DB_PATH = USER_DATA / 'PySender' / 'pysender.db'


def migrate_legacy_database():
    """On first startup, copy (never move/delete) the original app's SQLite file."""
    if CUSTOM_DATA_DIR or DB_PATH.exists() or not LEGACY_DB_PATH.is_file():
        return
    ROOT.mkdir(parents=True, exist_ok=True)
    # Copy while the source can still be read. SQLite online backup includes
    # committed content even if the old DB uses a write-ahead log.
    try:
        with closing(sqlite3.connect(str(LEGACY_DB_PATH), timeout=15)) as old:
            with closing(sqlite3.connect(str(DB_PATH), timeout=15)) as new:
                old.backup(new)
    except Exception:
        # Never launch with an incomplete copy.
        if DB_PATH.exists():
            DB_PATH.unlink()
        raise



@contextmanager
def connect():
    """Each operation commits/rolls back and always closes its SQLite connection."""
    ROOT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=15)
    try:
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys = ON')
        con.execute('PRAGMA busy_timeout = 15000')
        with con:
            yield con
    finally:
        con.close()


def initialize_database():
    migrate_legacy_database()
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            app_hint TEXT NOT NULL DEFAULT '', provider TEXT NOT NULL DEFAULT 'auto',
            message_x INTEGER, message_y INTEGER, send_x INTEGER, send_y INTEGER,
            allow_foreground INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            message TEXT NOT NULL DEFAULT '', mode TEXT NOT NULL DEFAULT 'write',
            scheduled_at TEXT NOT NULL, recurrence TEXT NOT NULL DEFAULT 'once',
            status TEXT NOT NULL DEFAULT 'pending', result TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER,
            profile_name TEXT, run_at TEXT NOT NULL,
            status TEXT NOT NULL, details TEXT NOT NULL)''')
        migrations = {
            'profiles': {
                'app_hint': "TEXT NOT NULL DEFAULT ''", 'provider': "TEXT NOT NULL DEFAULT 'auto'",
                'message_x': 'INTEGER', 'message_y': 'INTEGER',
                'send_x': 'INTEGER', 'send_y': 'INTEGER',
                'allow_foreground': 'INTEGER NOT NULL DEFAULT 1',
                'default_message': "TEXT NOT NULL DEFAULT ''",
                'window_process': "TEXT NOT NULL DEFAULT ''",
                'window_title': "TEXT NOT NULL DEFAULT ''",
                'chat_url': "TEXT NOT NULL DEFAULT ''",
                'editor_hint': "TEXT NOT NULL DEFAULT ''",
                'wait_release': 'INTEGER NOT NULL DEFAULT 0',
                'send_count': 'INTEGER NOT NULL DEFAULT 1',
            },
            'tasks': {'recurrence': "TEXT NOT NULL DEFAULT 'once'", 'result': "TEXT DEFAULT ''"},
        }
        for name, cols in migrations.items():
            known = {r['name'] for r in c.execute(f'PRAGMA table_info({name})')}
            for col, spec in cols.items():
                if col not in known:
                    c.execute(f'ALTER TABLE {name} ADD COLUMN {col} {spec}')
        # Recupera tarefas que estavam sendo executadas quando a sessao anterior encerrou.
        c.execute("UPDATE tasks SET status='pending' WHERE status='running'")


def rows(sql, params=()):
    with connect() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def one(sql, params=()):
    with connect() as c:
        row = c.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql, params=()):
    with connect() as c:
        cur = c.execute(sql, params)
        return cur.lastrowid


def save_profile(name, app_hint='', provider='auto', allow_foreground=True, profile_id=None, *, window_process='', window_title='', chat_url='', editor_hint='', wait_release=False, send_count=1):
    name = name.strip()
    if not name:
        raise ValueError('Informe um nome para o perfil.')
    if provider not in ('auto', 'uia', 'coords', 'window'):
        raise ValueError('Mecanismo de automacao invalido.')
    if int(send_count) not in (1, 2, 3):
        raise ValueError('Escolha de 1 a 3 envios.')
    if (wait_release or int(send_count) > 1) and provider != 'window':
        raise ValueError('Espera e múltiplos envios requerem Janela + colar + Enter.')
    values = (name, app_hint.strip(), provider, int(bool(allow_foreground)),
              window_process, window_title, chat_url.strip(), editor_hint.strip(), int(bool(wait_release)), int(send_count))
    with connect() as c:
        if profile_id is None:
            cur = c.execute('''INSERT INTO profiles(name,app_hint,provider,allow_foreground,window_process,window_title,chat_url,editor_hint,wait_release,send_count)
                VALUES(?,?,?,?,?,?,?,?,?,?)''', values)
            return cur.lastrowid
        cur = c.execute('''UPDATE profiles SET name=?,app_hint=?,provider=?,allow_foreground=?,window_process=?,window_title=?,chat_url=?,editor_hint=?,wait_release=?,send_count=?
            WHERE id=?''', values + (profile_id,))
        if cur.rowcount != 1:
            raise ValueError('Perfil nao encontrado.')
        return profile_id


def set_coordinate(profile_id, field, x, y):
    if field not in ('message', 'send'):
        raise ValueError('Ponto de clique invalido.')
    with connect() as c:
        cur = c.execute(f'UPDATE profiles SET {field}_x=?, {field}_y=? WHERE id=?',
                        (int(x), int(y), profile_id))
        if cur.rowcount != 1:
            raise ValueError('Perfil nao encontrado.')


def save_draft(profile_id, message):
    with connect() as c:
        cur = c.execute('UPDATE profiles SET default_message=? WHERE id=?', (message, profile_id))
        if cur.rowcount != 1:
            raise ValueError('Perfil nao encontrado.')


def delete_profile(profile_id):
    with connect() as c:
        c.execute('DELETE FROM profiles WHERE id=?', (profile_id,))


def create_task(profile_id, message, mode, scheduled_at, recurrence='once'):
    if mode not in ('write', 'click') or recurrence not in ('once', 'daily', 'weekly'):
        raise ValueError('Modo ou repeticao invalida.')
    if mode == 'write' and not message.strip():
        raise ValueError('Digite uma mensagem antes de agendar.')
    with connect() as c:
        cur = c.execute('''INSERT INTO tasks(profile_id,message,mode,scheduled_at,recurrence)
            VALUES(?,?,?,?,?)''', (profile_id, message, mode, scheduled_at, recurrence))
        return cur.lastrowid


def finish_task(task, error=None, result=None):
    now = datetime.now().isoformat(timespec='seconds')
    success = error is None
    detail = str(error) if error else (result or 'Acao executada. Entrega ao destinatario nao confirmada.')
    with connect() as c:
        profile = c.execute('SELECT name FROM profiles WHERE id=?', (task['profile_id'],)).fetchone()
        c.execute('''INSERT INTO history(task_id,profile_name,run_at,status,details)
            VALUES(?,?,?,?,?)''', (task['id'], profile['name'] if profile else '(excluido)', now,
                                   'success' if success else 'error', detail))
        if not success:
            c.execute("UPDATE tasks SET status='error',result=? WHERE id=?", (detail, task['id']))
        elif task['recurrence'] == 'once':
            c.execute("UPDATE tasks SET status='done',result=? WHERE id=?", (detail, task['id']))
        else:
            t = datetime.fromisoformat(task['scheduled_at'])
            step = timedelta(days=1 if task['recurrence'] == 'daily' else 7)
            while t <= datetime.now():
                t += step
            c.execute("UPDATE tasks SET status='pending',scheduled_at=?,result=? WHERE id=?",
                      (t.isoformat(timespec='seconds'), detail, task['id']))
