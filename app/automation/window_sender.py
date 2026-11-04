"""Window discovery and explicit foreground delivery. No background claim."""
import os
import re
import sys
import time
from urllib.parse import urlsplit


def discord_route(link):
    url = urlsplit(link.strip())
    if url.scheme != 'https' or url.netloc not in ('discord.com', 'www.discord.com'):
        raise ValueError('Use um link https://discord.com/channels/... do chat.')
    match = re.fullmatch(r'/channels/(@me|[0-9]+)/([0-9]+)(?:/[0-9]+)?/?', url.path)
    if not match or url.query or url.fragment:
        raise ValueError('Link de chat Discord inválido.')
    return 'discord://-/channels/' + match[1] + '/' + match[2]


def list_windows():
    if sys.platform != 'win32':
        return []
    import psutil
    import win32gui
    import win32process
    result = []
    def visit(hwnd, _):
        title = win32gui.GetWindowText(hwnd)
        if not title or not win32gui.IsWindowVisible(hwnd):
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == os.getpid():
            return
        try:
            process = psutil.Process(pid).exe()
        except (psutil.Error, OSError):
            return
        result.append(dict(hwnd=hwnd, title=title, process=process,
                           minimized=bool(win32gui.IsIconic(hwnd)),
                           discord=os.path.basename(process).lower() in
                           ('discord.exe', 'discordcanary.exe', 'discordptb.exe')))
    win32gui.EnumWindows(visit, None)
    return sorted(result, key=lambda w: w['title'].casefold())


def resolve_window(profile, windows):
    process = (profile.get('window_process') or '').casefold()
    title = profile.get('window_title') or ''
    candidates = [w for w in windows if w['process'].casefold() == process]
    exact = [w for w in candidates if w['title'] == title]
    if len(exact) == 1:
        return exact[0]
    # Discord changes the title when changing conversations; restrict to its process.
    if len(candidates) == 1 and candidates[0]['discord']:
        return candidates[0]
    raise RuntimeError('A janela selecionada não está aberta ou ficou ambígua. Selecione-a novamente em Perfis.')


def choose_editor(editors, expected=''):
    usable = [e for e in editors if e.is_visible() and e.is_enabled() and e.is_keyboard_focusable()]
    if expected:
        usable = [e for e in usable if expected.casefold() in e.window_text().casefold()]
    if len(usable) != 1:
        raise RuntimeError('Não foi possível identificar um único campo de mensagem. '
                           'Informe em Perfis o nome acessível do campo (ex.: Mensagem #geral).')
    return usable[0]


def validate(profile, mode, message):
    if not profile.get('window_process'):
        raise ValueError('Escolha uma janela aberta em Perfis.')
    if not profile.get('allow_foreground'):
        raise ValueError('Autorize restaurar e focar a janela para enviar com Enter.')
    if mode == 'write' and not (message or '').strip():
        raise ValueError('Digite uma mensagem.')
    link = (profile.get('chat_url') or '').strip()
    if link:
        discord_route(link)
        if os.path.basename(profile['window_process'].replace('\\', '/')).lower() not in ('discord.exe','discordptb.exe','discordcanary.exe'):
            raise ValueError('O link de chat requer selecionar o aplicativo Discord desktop.')
        if not (profile.get('editor_hint') or '').strip():
            raise ValueError('Informe o nome do campo do chat para confirmar o destino após abrir o link.')


def send_window(profile, message, mode):
    validate(profile, mode, message)
    if sys.platform != 'win32':
        raise RuntimeError('A seleção de janelas requer Windows.')
    import pythoncom
    pythoncom.CoInitialize()
    try:
        return _send(profile, message, mode)
    finally:
        pythoncom.CoUninitialize()


def _send(profile, message, mode):
    import win32con
    import win32gui
    import pyautogui as pg
    import pyperclip
    from pywinauto import Desktop
    window = resolve_window(profile, list_windows())
    hwnd = window['hwnd']
    if profile.get('chat_url'):
        if not window['discord']:
            raise RuntimeError('A janela escolhida não é o Discord desktop.')
        os.startfile(discord_route(profile['chat_url']))
        # Route is client-dependent; the expected composer must be found before typing.
        time.sleep(2)
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    root = Desktop(backend='uia').window(handle=hwnd).wrapper_object()
    root.set_focus()
    deadline = time.monotonic() + 8
    while True:
        try:
            editor = choose_editor(root.descendants(control_type='Edit'), profile.get('editor_hint') or '')
            break
        except RuntimeError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.25)
    editor.set_focus()
    time.sleep(.15)
    def check_focus():
        if win32gui.GetForegroundWindow() != hwnd or not editor.has_keyboard_focus():
            raise RuntimeError('O foco mudou. Envio cancelado para não digitar em outra janela.')
    check_focus()
    if mode == 'write':
        # Refuse to append to an existing draft. Unsupported value patterns fail closed.
        try:
            existing = editor.get_value()
        except Exception as exc:
            raise RuntimeError('O aplicativo não permite verificar o rascunho desse campo. Envio cancelado.') from exc
        if existing:
            raise RuntimeError('O chat já contém um rascunho. Limpe o campo antes do envio automático.')
        previous = pyperclip.paste()
        try:
            pyperclip.copy(message)
            check_focus()
            pg.hotkey('ctrl', 'v')
            time.sleep(.3)
            check_focus()
            if editor.get_value().replace('\r\n', '\n') != message.replace('\r\n', '\n'):
                raise RuntimeError('O texto colado não pôde ser confirmado. Enter não foi enviado.')
        finally:
            if pyperclip.paste() == message:
                pyperclip.copy(previous)
    check_focus()
    pg.press('enter')
    return 'Enter enviado à janela selecionada. Recebimento da mensagem não confirmado.'
