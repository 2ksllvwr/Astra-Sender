"""Astra Sender 0.2.4: interface compacta com quatro abas superiores.

Todas as operações do usuário são persistidas no SQLite; o envio é gerenciado
pelo mesmo motor da versão anterior. A interface não declara entrega confirmada.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTimer, QDateTime, QDate, QTime
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QCheckBox, QComboBox, QDateTimeEdit,
    QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QPushButton, QStyle, QSystemTrayIcon,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from app.automation.engine import send
from app.database import db
from app.ui.selector import Selector

VERSION = '0.2.8'
STYLE = """
QWidget { background-color: #111b2a; color: #e7edf6; font: 10pt 'Segoe UI'; }
QMainWindow { background-color: #0a1422; }
QTabWidget::pane { border: 1px solid #2b3d53; background: #111b2a;
    border-radius: 5px; top: -1px; }
QTabBar::tab { background: transparent; color: #d0d9e6; padding: 10px 18px;
    border: 0; margin-right: 2px; min-width: 82px; }
QTabBar::tab:hover:!selected { background: #1e3047; border-radius: 5px; }
QTabBar::tab:selected { background: #1477eb; color: white;
    border-radius: 5px; font-weight: 600; }
QLabel#muted { color: #9cacc0; }
QLabel#ready { color: #6cdda5; }
QLabel#hint { color: #9db0c5; }
QPushButton { padding: 6px 12px; min-height: 25px; border-radius: 5px;
    background: #24374d; border: 1px solid #364f6c; color: #edf3fc; }
QPushButton:hover { background: #304e6a; }
QPushButton:pressed { background: #386080; }
QPushButton:disabled { color: #6f8093; background: #192638; border-color: #273447; }
QPushButton#primary { background: #1179f0; border-color: #2787f5; font-weight: 600; }
QPushButton#primary:hover { background: #2a90ff; }
QPushButton#send { background: #279745; border-color: #38a957; font-weight: 600; }
QPushButton#send:hover { background: #35aa55; }
QPushButton#small { min-width: 25px; max-width: 33px; padding: 5px 3px; font-size: 13pt; }
QLineEdit, QTextEdit, QComboBox, QDateTimeEdit {
    background: #1d2e42; color: #f1f5fd; border: 1px solid #354e69;
    selection-background-color: #187aea; border-radius: 5px; padding: 6px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border-color: #398fee; }
QComboBox { min-height: 25px; }
QComboBox QAbstractItemView { background: #1d2e42; selection-background-color: #175da6; }
QTableWidget { border: 1px solid #2b3d53; border-radius: 5px;
    background: #152338; alternate-background-color: #1a2a40;
    gridline-color: transparent; selection-background-color: #1e5790; }
QTableWidget::item { padding: 5px 4px; }
QHeaderView::section { background: #22374e; color: #e6efff;
    border: 0; border-right: 1px solid #2c415a; padding: 8px 5px; }
QCheckBox { spacing: 7px; }
QStatusBar { background: #0b1727; color: #a3b2c5; border-top: 1px solid #26374d; }
QStatusBar::item { border: none; }
"""


def button(text, callback, kind=None, tip=None):
    b = QPushButton(text)
    if kind:
        b.setObjectName(kind)
    if tip:
        b.setToolTip(tip)
    b.clicked.connect(callback)
    return b


def table_widget(headers):
    w = QTableWidget(0, len(headers))
    w.setHorizontalHeaderLabels(headers)
    w.setAlternatingRowColors(True)
    w.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    w.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    w.verticalHeader().hide()
    w.setShowGrid(False)
    return w


def formatted_time(s):
    try:
        return datetime.fromisoformat(s).strftime('%d/%m/%Y %H:%M:%S')
    except (ValueError, TypeError):
        return str(s or '')


def qt_datetime(pydate):
    """PySide6 expects QDate+QTime, not five positional integer arguments."""
    return QDateTime(QDate(pydate.year, pydate.month, pydate.day),
                     QTime(pydate.hour, pydate.minute, pydate.second))


class ProfileDialog(QDialog):
    def __init__(self, parent, record=None):
        super().__init__(parent)
        self.record = record or {}
        self.saved_id = None
        self.setWindowTitle('Editar perfil' if record else 'Novo perfil')
        self.setMinimumWidth(430)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(self.record.get('name') or '')
        self.name.setPlaceholderText('Ex.: WhatsApp, Discord, Telegram')
        self.hint = QLineEdit(self.record.get('app_hint') or '')
        self.hint.setPlaceholderText('Parte do título da janela (opcional)')
        self.provider = QComboBox()
        self.provider.addItem('Janela + colar + Enter', 'window')
        self.provider.addItem('Automático (UIA / mouse)', 'auto')
        self.provider.addItem('Apenas mouse / coordenadas', 'coords')
        self.provider.addItem('Apenas acessibilidade (UIA)', 'uia')
        i = self.provider.findData(self.record.get('provider') or 'window')
        self.provider.setCurrentIndex(max(0, i))
        self.allow = QCheckBox('Permitir uso do mouse/teclado quando necessário')
        self.allow.setChecked(bool(self.record.get('allow_foreground', 1)))
        self.provider.currentIndexChanged.connect(self.update_permission)
        form.addRow('Nome', self.name)
        form.addRow('Janela', self.hint)
        form.addRow('Método', self.provider)
        self.windows = QComboBox()
        self.windows.setMinimumWidth(320)
        self.windows.currentIndexChanged.connect(self.window_changed)
        window_row = QHBoxLayout()
        window_row.addWidget(self.windows, 1)
        window_row.addWidget(button('Atualizar', self.refresh_windows))
        form.addRow('Janelas abertas', window_row)
        self.chat = QLineEdit(self.record.get('chat_url') or '')
        self.chat.setPlaceholderText('https://discord.com/channels/... (opcional)')
        form.addRow('Chat do Discord', self.chat)
        self.editor = QLineEdit(self.record.get('editor_hint') or '')
        self.editor.setPlaceholderText('Automático no Discord; use Detectar campos para fixar o chat')
        editor_row = QHBoxLayout()
        editor_row.addWidget(self.editor, 1)
        editor_row.addWidget(button('Detectar campos', self.detect_fields))
        editor_row.addWidget(button('Diagnóstico', self.diagnose_fields))
        form.addRow('Campo de texto', editor_row)
        self.refresh_windows()

        layout.addLayout(form)
        layout.addWidget(self.allow)
        explanation = QLabel('Janela + Enter restaura o destino e cola a mensagem de uma vez. '
                             'Não precisa marcar o botão de envio. O envio usa o foco do teclado; '
                             'tarefas simultâneas são executadas em sequência. '
                             'No Discord, o campo é detectado automaticamente. Com link, abra o chat desejado antes de salvar o perfil.')
        explanation.setObjectName('muted')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.update_permission()
        controls = QHBoxLayout()
        controls.addStretch()
        controls.addWidget(button('Cancelar', self.reject))
        controls.addWidget(button('Salvar perfil', self.save, 'primary'))
        layout.addLayout(controls)

    def refresh_windows(self):
        from app.automation.window_sender import list_windows
        current = self.windows.currentData() or self.record
        self.windows.blockSignals(True)
        self.windows.clear()
        self.windows.addItem('Selecione uma janela…', None)
        try:
            for w in list_windows():
                prefix = 'Discord · ' if w['discord'] else ''
                suffix = ' (minimizada)' if w['minimized'] else ''
                self.windows.addItem(prefix + w['title'] + suffix, w)
                if (w['process'] == current.get('process', current.get('window_process')) and
                        w['title'] == current.get('title', current.get('window_title'))):
                    self.windows.setCurrentIndex(self.windows.count() - 1)
        except Exception as exc:
            QMessageBox.warning(self, 'Janelas', str(exc))
        self.windows.blockSignals(False)
        self.window_changed()

    def window_changed(self):
        if not hasattr(self, 'chat'):
            return
        w = self.windows.currentData()
        is_discord = bool(w and w['discord'])
        self.chat.setEnabled(is_discord)
        if w and not self.name.text().strip():
            self.name.setText('Discord' if is_discord else w['title'])

    def detect_fields(self):
        w = self.windows.currentData()
        if not w:
            return QMessageBox.information(self, 'Campos', 'Selecione uma janela aberta primeiro.')
        try:
            from pywinauto import Desktop
            root = Desktop(backend='uia').window(handle=w['hwnd']).wrapper_object()
            from app.automation.window_sender import discover_editors, choose_editor, editor_name, normalized_name
            if root.is_minimized():
                root.restore()
            candidates = discover_editors(root, w['discord'])
            try:
                chosen = choose_editor(candidates, discord=w['discord'])
            except RuntimeError:
                chosen = None
            if chosen is not None:
                self.editor.setText(editor_name(chosen))
                return
            fields = [editor_name(e) for e in candidates]
            fields = list(dict.fromkeys(n for n in fields if normalized_name(n)))
            if not fields:
                raise RuntimeError(f'Foram encontrados {len(candidates)} campos, mas nenhum com nome acessível. '
                                   'O Discord pode não estar expondo os rótulos ao Windows. '
                                   'Nenhuma mensagem foi enviada.')
            from PySide6.QtWidgets import QInputDialog
            choice, ok = QInputDialog.getItem(self, 'Campo de mensagem',
                                              'Selecione o campo usado para escrever (não a pesquisa):', fields, 0, False)
            if ok:
                self.editor.setText(choice)
        except Exception as exc:
            QMessageBox.warning(self, 'Detectar campos', str(exc))

    def diagnose_fields(self):
        w = self.windows.currentData()
        if not w:
            return QMessageBox.information(self, 'Diagnóstico', 'Selecione uma janela primeiro.')
        try:
            from pywinauto import Desktop
            from app.automation.window_sender import field_diagnostics
            root = Desktop(backend='uia').window(handle=w['hwnd']).wrapper_object()
            report = field_diagnostics(root)
            dialog = QDialog(self)
            dialog.setWindowTitle('Diagnóstico dos campos — copie o texto para análise')
            dialog.resize(780, 430)
            layout = QVBoxLayout(dialog)
            text = QTextEdit()
            text.setReadOnly(True)
            text.setPlainText(report)
            layout.addWidget(text)
            layout.addWidget(button('Copiar diagnóstico', lambda: QApplication.clipboard().setText(report)))
            layout.addWidget(button('Fechar', dialog.accept))
            dialog.exec()
        except Exception as exc:
            QMessageBox.warning(self, 'Diagnóstico', str(exc))

    def update_permission(self):
        uia_only = self.provider.currentData() == 'uia'
        self.allow.setEnabled(not uia_only)
        if uia_only:
            self.allow.setChecked(False)

    def save(self):
        try:
            w = self.windows.currentData()
            options = dict(window_process=(w or {}).get('process', self.record.get('window_process', '')),
                           window_title=(w or {}).get('title', self.record.get('window_title', '')),
                           chat_url=self.chat.text() if self.chat.isEnabled() else '',
                           editor_hint=self.editor.text())
            if (self.provider.currentData() == 'window' and options['chat_url'].strip()
                    and not options['editor_hint'].strip()):
                self.detect_fields()
                options['editor_hint'] = self.editor.text()
            if self.provider.currentData() == 'window':
                from app.automation.window_sender import validate
                validate(dict(options, allow_foreground=self.allow.isChecked()), 'click', '')
            self.saved_id = db.save_profile(self.name.text(), self.hint.text(),
                                            self.provider.currentData(), self.allow.isChecked(),
                                            self.record.get('id'), **options)
        except Exception as exc:
            QMessageBox.critical(self, 'Falha ao salvar', str(exc))
            return
        self.accept()


class ScheduleDialog(QDialog):
    """Formulário separado para a área principal permanecer compacta."""
    def __init__(self, parent, profile_id=None, task=None, draft='', mode='write'):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle('Editar agendamento' if task else 'Novo agendamento')
        self.setMinimumWidth(505)
        self.setStyleSheet(STYLE)
        body = QVBoxLayout(self)
        form = QFormLayout()
        self.profile = QComboBox()
        for p in db.rows('SELECT id, name FROM profiles ORDER BY name COLLATE NOCASE'):
            self.profile.addItem(p['name'], p['id'])
        selected = task['profile_id'] if task else profile_id
        index = self.profile.findData(selected)
        if index >= 0:
            self.profile.setCurrentIndex(index)
        self.mode = QComboBox()
        self.mode.addItem('Escrever e enviar', 'write')
        self.mode.addItem('Somente enviar (Enter ou botão)', 'click')
        mode = task['mode'] if task else mode
        i = self.mode.findData(mode)
        self.mode.setCurrentIndex(max(0, i))
        self.message = QTextEdit()
        self.message.setPlaceholderText('Mensagem do agendamento')
        self.message.setFixedHeight(100)
        self.message.setPlainText((task['message'] if task else draft) or '')
        self.when = QDateTimeEdit()
        self.when.setDisplayFormat('dd/MM/yyyy HH:mm:ss')
        self.when.setCalendarPopup(True)
        d = datetime.fromisoformat(task['scheduled_at']) if task else (datetime.now() + timedelta(minutes=5)).replace(second=0, microsecond=0)
        self.when.setDateTime(qt_datetime(d))
        self.recurrence = QComboBox()
        self.recurrence.addItem('Uma vez', 'once')
        self.recurrence.addItem('Diariamente', 'daily')
        self.recurrence.addItem('Semanalmente', 'weekly')
        if task:
            self.recurrence.setCurrentIndex(max(0, self.recurrence.findData(task['recurrence'])))
        form.addRow('Perfil', self.profile)
        form.addRow('Modo', self.mode)
        form.addRow('Mensagem', self.message)
        form.addRow('Data e horário', self.when)
        note = QLabel('Janela + Enter prepara o texto até 12 s antes. Mantenha o chat livre até o disparo. Segundos :00 = virada do minuto.')
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow('Repetição', self.recurrence)
        body.addLayout(form)
        foot = QHBoxLayout()
        foot.addStretch()
        foot.addWidget(button('Cancelar', self.reject))
        foot.addWidget(button('Salvar agendamento', self.save, 'primary'))
        body.addLayout(foot)
        self.mode.currentIndexChanged.connect(self.change_mode)
        self.change_mode()

    def change_mode(self):
        self.message.setEnabled(self.mode.currentData() == 'write')

    def save(self):
        pid = self.profile.currentData()
        p = db.one('SELECT * FROM profiles WHERE id=?', (pid,)) if pid else None
        mode = self.mode.currentData()
        err = MainWindow.validate_profile(p, mode, self.message.toPlainText())
        if err:
            QMessageBox.warning(self, 'Configuração incompleta', err)
            return
        if self.when.dateTime().toPython() <= datetime.now():
            QMessageBox.warning(self, 'Data inválida', 'Escolha uma data e horário futuros.')
            return
        self.accept()

    def values(self):
        return (self.profile.currentData(), self.message.toPlainText(),
                self.mode.currentData(),
                self.when.dateTime().toPython().isoformat(timespec='seconds'),
                self.recurrence.currentData())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Astra Sender')
        self.resize(790, 470)
        self.setMinimumSize(650, 400)
        self.setStyleSheet(STYLE)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.future = None
        self.running_task = None
        self.picker = None
        self.exiting = False
        self._refreshing_profile = False

        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(10, 8, 10, 6)
        outer.setSpacing(5)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        self.setCentralWidget(content)
        self.build_send_tab()
        self.build_tasks_tab()
        self.build_history_tab()
        self.build_profiles_tab()

        self.status = QLabel('●  Pronto')
        self.status.setObjectName('ready')
        self.statusBar().addWidget(self.status, 1)
        self.statusBar().addPermanentWidget(QLabel(f'Astra Sender {VERSION}'))
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self)
        tray_menu = QMenu(self)
        tray_menu.addAction('Abrir Astra Sender', self.show_normal)
        tray_menu.addAction('Sair', self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(lambda reason: self.show_normal()
                                    if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        QApplication.instance().setQuitOnLastWindowClosed(not self.tray.isVisible())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.start(100)
        self.refresh_profiles()
        self.refresh_tasks()
        self.refresh_history()

    def build_send_tab(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(15, 16, 15, 13)
        v.setSpacing(13)
        top = QHBoxLayout()
        caption = QLabel('Perfil:')
        caption.setFixedWidth(72)
        top.addWidget(caption)
        self.profile = QComboBox()
        self.profile.setMinimumWidth(180)
        top.addWidget(self.profile, 1)
        top.addWidget(button('+', self.new_profile, 'small', 'Criar perfil'))
        top.addWidget(button('✎', self.edit_profile, 'small', 'Editar perfil'))
        top.addWidget(button('⌖', self.show_points_menu, 'small', 'Selecionar campo ou botão de enviar'))
        self.profile.currentIndexChanged.connect(self.profile_changed)
        v.addLayout(top)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel('Modo:'))
        self.mode = QComboBox()
        self.mode.addItem('Escrever e enviar', 'write')
        self.mode.addItem('Somente enviar', 'click')
        self.mode.currentIndexChanged.connect(self.change_mode)
        mode_row.addWidget(self.mode)
        mode_row.addStretch()
        self.coord_label = QLabel('Campo: —   |   Envio: —')
        self.coord_label.setObjectName('muted')
        mode_row.addWidget(self.coord_label)
        v.addLayout(mode_row)

        msg_row = QHBoxLayout()
        msg_row.setAlignment(Qt.AlignmentFlag.AlignTop)
        msg_label = QLabel('Mensagem:')
        msg_label.setFixedWidth(72)
        msg_row.addWidget(msg_label)
        self.message = QTextEdit()
        self.message.setPlaceholderText('Escreva sua mensagem aqui...')
        self.message.setMinimumHeight(120)
        msg_row.addWidget(self.message, 1)
        v.addLayout(msg_row, 1)

        buttons = QHBoxLayout()
        buttons.addSpacing(78)
        buttons.addWidget(button('▶  Enviar Agora', self.send_now, 'send'))
        buttons.addStretch()
        buttons.addWidget(button('Salvar Mensagem', self.save_draft))
        buttons.addWidget(button('Agendar...', self.new_task, 'primary'))
        v.addLayout(buttons)
        v.addStretch(1)
        self.tabs.addTab(page, 'Enviar')

    def build_tasks_tab(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(11, 12, 11, 10)
        v.setSpacing(11)
        self.task_table = table_widget(['#', 'Perfil', 'Mensagem (resumo)', 'Data/Horário', 'Repetição', 'Status'])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.doubleClicked.connect(lambda _: self.edit_task())
        v.addWidget(self.task_table, 1)
        bar = QHBoxLayout()
        bar.addWidget(button('+ Novo', self.new_task, 'primary'))
        bar.addWidget(button('Editar', self.edit_task))
        bar.addWidget(button('Pausar / Retomar', self.pause_task))
        bar.addWidget(button('Excluir', self.delete_task))
        bar.addStretch()
        bar.addWidget(button('Executar agora', self.run_task_now))
        v.addLayout(bar)
        self.tabs.addTab(page, 'Agendamentos')

    def build_history_tab(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(11, 12, 11, 10)
        v.setSpacing(11)
        self.history_table = table_widget(['Data/Hora', 'Perfil', 'Resultado', 'Detalhes'])
        v.addWidget(self.history_table, 1)
        bar = QHBoxLayout()
        bar.addWidget(button('Atualizar', self.refresh_history))
        bar.addStretch()
        label = QLabel('Registro de ações; entrega não confirmada.')
        label.setObjectName('muted')
        bar.addWidget(label)
        v.addLayout(bar)
        self.tabs.addTab(page, 'Histórico')

    def build_profiles_tab(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(11, 12, 11, 10)
        v.setSpacing(11)
        self.profiles_table = table_widget(['Perfil', 'Janela', 'Método', 'Campo', 'Botão de envio'])
        self.profiles_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.profiles_table.setColumnWidth(0, 155)
        self.profiles_table.doubleClicked.connect(lambda _: self.edit_profile())
        self.profiles_table.itemSelectionChanged.connect(self.profile_table_selected)
        v.addWidget(self.profiles_table, 1)
        bar = QHBoxLayout()
        bar.addWidget(button('+ Novo', self.new_profile, 'primary'))
        bar.addWidget(button('Editar', self.edit_profile))
        bar.addWidget(button('Excluir', self.delete_profile))
        bar.addStretch()
        bar.addWidget(button('Marcar campo', lambda: self.pick_point('message')))
        bar.addWidget(button('Marcar envio', lambda: self.pick_point('send')))
        v.addLayout(bar)
        self.tabs.addTab(page, 'Perfis')

    def notify(self, message):
        self.status.setText('●  ' + message)
        self.statusBar().showMessage(message, 5000)

    def alert(self, title, message):
        QMessageBox.warning(self, title, message)
        self.notify(message)

    def selected_profile(self):
        pid = self.profile.currentData()
        return db.one('SELECT * FROM profiles WHERE id=?', (pid,)) if pid else None

    def refresh_profiles(self, select_id=None):
        prior = select_id if select_id is not None else self.profile.currentData()
        self._refreshing_profile = True
        self.profile.clear()
        profiles = db.rows('SELECT * FROM profiles ORDER BY name COLLATE NOCASE')
        for p in profiles:
            self.profile.addItem(p['name'], p['id'])
        index = self.profile.findData(prior)
        if index >= 0:
            self.profile.setCurrentIndex(index)
        self.profiles_table.setRowCount(len(profiles))
        for row, p in enumerate(profiles):
            items = [p['name'], p['app_hint'] or '—',
                     {'window': 'Janela + Enter', 'auto': 'Automático', 'coords': 'Coordenadas', 'uia': 'UIA'}.get(p['provider'], p['provider']),
                     self.coord_string(p, 'message'), self.coord_string(p, 'send')]
            for col, value in enumerate(items):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, p['id'])
                self.profiles_table.setItem(row, col, item)
        self._refreshing_profile = False
        self.profile_changed()

    @staticmethod
    def coord_string(p, field):
        x, y = p.get(field + '_x'), p.get(field + '_y')
        return f'{x}, {y}' if x is not None and y is not None else 'Não marcado'

    def profile_changed(self):
        if self._refreshing_profile:
            return
        p = self.selected_profile()
        self.message.setPlainText((p or {}).get('default_message') or '')
        if p:
            self.coord_label.setText('Campo: ' + self.coord_string(p, 'message') +
                                     '   |   Envio: ' + self.coord_string(p, 'send'))
            if p.get('provider') == 'window':
                self.coord_label.setText('Janela selecionada · Colar + Enter')
            for row in range(self.profiles_table.rowCount()):
                item = self.profiles_table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == p['id']:
                    self._refreshing_profile = True
                    self.profiles_table.selectRow(row)
                    self._refreshing_profile = False
                    break
        else:
            self.coord_label.setText('Campo: —   |   Envio: —')

    def profile_table_selected(self):
        if self._refreshing_profile or self.tabs.currentIndex() != 3:
            return
        items = self.profiles_table.selectedItems()
        if not items:
            return
        pid = self.profiles_table.item(items[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        i = self.profile.findData(pid)
        if i >= 0 and i != self.profile.currentIndex():
            self.profile.setCurrentIndex(i)

    def new_profile(self):
        dialog = ProfileDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_profiles(dialog.saved_id)
            self.notify('Perfil salvo. Marque os pontos quando desejar.')

    def edit_profile(self):
        p = self.selected_profile()
        if not p:
            return self.alert('Perfil', 'Crie ou selecione um perfil primeiro.')
        dialog = ProfileDialog(self, p)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_profiles(dialog.saved_id)
            self.notify('Perfil atualizado.')

    def delete_profile(self):
        p = self.selected_profile()
        if not p:
            return self.alert('Perfil', 'Selecione um perfil.')
        if self.running_task and self.running_task['profile_id'] == p['id']:
            return self.alert('Perfil', 'Há um envio em andamento neste perfil.')
        if QMessageBox.question(self, 'Excluir perfil',
                                f'Excluir "{p["name"]}" e seus agendamentos?') != QMessageBox.StandardButton.Yes:
            return
        try:
            db.delete_profile(p['id'])
            self.refresh_profiles()
            self.refresh_tasks()
            self.notify('Perfil excluído.')
        except Exception as exc:
            self.alert('Falha ao excluir', str(exc))

    def show_points_menu(self):
        if not self.selected_profile():
            return self.alert('Perfil', 'Crie um perfil antes de marcar pontos.')
        menu = QMenu(self)
        menu.addAction('Marcar campo de mensagem', lambda: self.pick_point('message'))
        menu.addAction('Marcar botão de enviar', lambda: self.pick_point('send'))
        menu.exec(self.profile.mapToGlobal(self.profile.rect().bottomLeft()))

    def pick_point(self, field):
        p = self.selected_profile()
        if not p:
            return self.alert('Perfil', 'Crie um perfil antes de marcar pontos.')
        self.notify('Clique no campo ou botão da outra janela. Esc cancela.')
        self.picker = Selector(self, 'Campo da mensagem' if field == 'message' else 'Botão de enviar',
                               lambda x, y: self.picked(p['id'], field, x, y))

    def picked(self, pid, field, x, y):
        try:
            db.set_coordinate(pid, field, x, y)
            self.refresh_profiles(pid)
            self.notify(f'Ponto salvo: X={x}, Y={y}')
        except Exception as exc:
            self.alert('Falha ao gravar ponto', str(exc))
        finally:
            self.picker = None

    def change_mode(self):
        self.message.setEnabled(self.mode.currentData() == 'write')

    def save_draft(self):
        p = self.selected_profile()
        if not p:
            return self.alert('Perfil', 'Crie ou selecione um perfil antes de salvar.')
        try:
            db.save_draft(p['id'], self.message.toPlainText())
            self.notify('Mensagem salva no perfil.')
        except Exception as exc:
            self.alert('Erro ao salvar', str(exc))

    @staticmethod
    def validate_profile(profile, mode, message):
        if not profile:
            return 'Crie ou selecione um perfil.'
        if profile.get('provider') == 'window':
            from app.automation.window_sender import validate
            try:
                validate(profile, mode, message)
            except ValueError as exc:
                return str(exc)
            return None
        if profile.get('send_x') is None or profile.get('send_y') is None:
            return 'Marque o botão de enviar no perfil.'
        if mode == 'write':
            if profile.get('message_x') is None or profile.get('message_y') is None:
                return 'Marque o campo de mensagem no perfil.'
            if not (message or '').strip():
                return 'Digite uma mensagem.'
        if profile.get('provider') == 'coords' and not profile.get('allow_foreground'):
            return 'Autorize mouse/teclado no perfil ou escolha outro método.'
        return None

    def check_ready(self):
        p = self.selected_profile()
        error = self.validate_profile(p, self.mode.currentData(), self.message.toPlainText())
        if error:
            self.alert('Configuração incompleta', error)
            return None
        return p

    def new_task(self):
        p = self.selected_profile()
        if not p:
            return self.alert('Perfil', 'Crie um perfil antes de agendar.')
        dialog = ScheduleDialog(self, profile_id=p['id'], draft=self.message.toPlainText(),
                                mode=self.mode.currentData())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_task_values(dialog.values())

    def save_task_values(self, values, task_id=None):
        try:
            pid, message, mode, date, recurrence = values
            if task_id is None:
                db.create_task(pid, message, mode, date, recurrence)
            else:
                existing = db.one('SELECT status FROM tasks WHERE id=?', (task_id,))
                if not existing or existing['status'] == 'running':
                    raise ValueError('Agendamento indisponível para edição.')
                db.execute('''UPDATE tasks SET profile_id=?, message=?, mode=?, scheduled_at=?,
                    recurrence=?, status='pending', result='' WHERE id=?''',
                    (pid, message, mode, date, recurrence, task_id))
            db.save_draft(pid, message)
            self.refresh_tasks()
            self.tabs.setCurrentIndex(1)
            self.notify('Agendamento salvo.')
        except Exception as exc:
            self.alert('Falha ao salvar agendamento', str(exc))

    def selected_task(self):
        items = self.task_table.selectedItems()
        if not items:
            return None
        i = self.task_table.item(items[0].row(), 0)
        return db.one('SELECT * FROM tasks WHERE id=?',
                      (i.data(Qt.ItemDataRole.UserRole),)) if i else None

    def refresh_tasks(self):
        records = db.rows('''SELECT t.*, p.name profile_name FROM tasks t
            LEFT JOIN profiles p ON p.id=t.profile_id ORDER BY t.scheduled_at DESC''')
        self.task_table.setRowCount(len(records))
        trans = {'pending': 'Ativo', 'paused': 'Pausado', 'running': 'Executando',
                 'done': 'Concluído', 'error': 'Erro'}
        for row, t in enumerate(records):
            summary = (t['message'] or '').replace('\n', ' ')
            if t['mode'] == 'click':
                summary = '(somente clique)'
            if len(summary) > 47:
                summary = summary[:44] + '...'
            vals = [str(t['id']), t['profile_name'] or '(excluído)', summary,
                    formatted_time(t['scheduled_at']),
                    {'once': 'Única', 'daily': 'Diária', 'weekly': 'Semanal'}.get(t['recurrence'], t['recurrence']),
                    trans.get(t['status'], t['status'])]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, t['id'])
                self.task_table.setItem(row, col, item)
        active = sum(t['status'] == 'pending' for t in records)
        if self.future:
            self.status.setText('●  Executando automação...')
        elif not self.status.text().startswith('●  Perfil'):
            self.status.setText(f'●  Pronto — {active} agendamento(s) ativo(s)')

    def edit_task(self):
        t = self.selected_task()
        if not t:
            return self.alert('Agendamentos', 'Selecione um agendamento.')
        if t['status'] == 'running':
            return self.alert('Agendamentos', 'Não é possível editar durante a execução.')
        dialog = ScheduleDialog(self, task=t)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_task_values(dialog.values(), t['id'])

    def pause_task(self):
        t = self.selected_task()
        if not t:
            return self.alert('Agendamentos', 'Selecione um agendamento.')
        if t['status'] not in ('pending', 'paused'):
            return self.alert('Agendamentos', 'Somente agendamentos ativos ou pausados podem ser alternados.')
        status = 'paused' if t['status'] == 'pending' else 'pending'
        db.execute('UPDATE tasks SET status=? WHERE id=?', (status, t['id']))
        self.refresh_tasks()
        self.notify('Agendamento ' + ('pausado.' if status == 'paused' else 'retomado.'))

    def delete_task(self):
        t = self.selected_task()
        if not t:
            return self.alert('Agendamentos', 'Selecione um agendamento.')
        if t['status'] == 'running':
            return self.alert('Agendamentos', 'Não é possível excluir durante a execução.')
        if QMessageBox.question(self, 'Excluir agendamento', 'Excluir o agendamento selecionado?') == QMessageBox.StandardButton.Yes:
            db.execute('DELETE FROM tasks WHERE id=?', (t['id'],))
            self.refresh_tasks()
            self.notify('Agendamento excluído.')

    def run_task_now(self):
        t = self.selected_task()
        if not t:
            return self.alert('Agendamentos', 'Selecione um agendamento.')
        if t['status'] == 'running':
            return self.alert('Agendamentos', 'Já está em execução.')
        if QMessageBox.question(self, 'Executar agora', 'Executar o agendamento selecionado agora?') == QMessageBox.StandardButton.Yes:
            self.dispatch(t)

    def send_now(self):
        p = self.check_ready()
        if not p:
            return
        if self.future is not None:
            return self.alert('Envio em andamento', 'Já existe uma automação em execução.')
        if QMessageBox.question(self, 'Enviar agora', f'Executar envio no perfil "{p["name"]}"?') != QMessageBox.StandardButton.Yes:
            return
        try:
            task_id = db.create_task(p['id'], self.message.toPlainText(), self.mode.currentData(),
                                     datetime.now().isoformat(timespec='seconds'))
            self.dispatch(db.one('SELECT * FROM tasks WHERE id=?', (task_id,)))
        except Exception as exc:
            self.alert('Falha ao enviar', str(exc))

    def refresh_history(self):
        records = db.rows('SELECT * FROM history ORDER BY id DESC LIMIT 300')
        self.history_table.setRowCount(len(records))
        for row, h in enumerate(records):
            vals = [formatted_time(h['run_at']), h['profile_name'] or '',
                    'Ação executada' if h['status'] == 'success' else 'Falha', h['details']]
            for col, val in enumerate(vals):
                self.history_table.setItem(row, col, QTableWidgetItem(str(val)))

    def dispatch(self, task, scheduled=False):
        if self.future is not None:
            self.notify('Outra automação já está em execução.')
            return
        p = db.one('SELECT * FROM profiles WHERE id=?', (task['profile_id'],))
        if not p:
            db.finish_task(task, error='Perfil não encontrado.')
            self.refresh_tasks()
            self.refresh_history()
            return
        error = self.validate_profile(p, task['mode'], task['message'])
        if error:
            db.finish_task(task, error=error)
            self.refresh_tasks()
            self.refresh_history()
            self.notify('Falha: ' + error)
            return
        db.execute("UPDATE tasks SET status='running' WHERE id=?", (task['id'],))
        self.running_task = task
        target = datetime.fromisoformat(task['scheduled_at']).timestamp() if scheduled and p['provider'] == 'window' else None
        self.future = self.executor.submit(send, p, task['message'], task['mode'], target)
        self.refresh_tasks()
        self.notify('Preparando envio; mantenha o destino livre até o horário.' if target else 'Executando automação...')

    def tick(self):
        if self.future is not None:
            if not self.future.done():
                return
            try:
                result = self.future.result()
                error = None
            except Exception as exc:
                error, result = str(exc), None
            db.finish_task(self.running_task, error=error, result=result)
            self.future = None
            self.running_task = None
            self.refresh_tasks()
            self.refresh_history()
            self.notify('Falha: ' + error if error else 'Ação executada; entrega não confirmada.')
        from app.automation.timing import PREPARE_SECONDS
        now = datetime.now()
        t = db.one("SELECT t.* FROM tasks t JOIN profiles p ON p.id=t.profile_id "
                   "WHERE t.status='pending' AND (t.scheduled_at<=? OR "
                   "(p.provider='window' AND t.scheduled_at<=?)) ORDER BY t.scheduled_at LIMIT 1",
                   (now.isoformat(timespec='seconds'),
                    (now + timedelta(seconds=PREPARE_SECONDS)).isoformat(timespec='seconds')))
        if t:
            self.dispatch(t, scheduled=True)

    def show_normal(self):
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if not self.exiting and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage('Astra Sender', 'Agendamentos permanecem ativos na bandeja.',
                                  QSystemTrayIcon.MessageIcon.Information, 1500)
        elif self.future and not self.future.done():
            event.ignore()
            self.alert('Envio ativo', 'Aguarde a conclusão da ação antes de sair.')
        else:
            self.timer.stop()
            self.executor.shutdown(wait=False)
            event.accept()

    def quit_app(self):
        if self.future and not self.future.done():
            return self.alert('Envio ativo', 'Conclua a ação atual antes de sair.')
        self.exiting = True
        self.timer.stop()
        self.tray.hide()
        self.executor.shutdown(wait=False)
        QApplication.quit()
