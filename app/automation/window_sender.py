"""Window discovery and explicit foreground delivery. No background claim."""
import os
import re
import sys
import time
import unicodedata
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


def editor_name(editor):
    """Accessible label, never TextPattern contents or the current draft."""
    for read in (lambda: editor.element_info.name,
                 lambda: editor.iface_legacy_iaccessible.CurrentName):
        try:
            name = read()
            if isinstance(name, str) and normalized_name(name):
                return name
        except Exception:
            pass
    return ''


def normalized_name(value):
    value = unicodedata.normalize('NFKC', value).casefold()
    return ' '.join(''.join(c for c in value if unicodedata.category(c) != 'Cf').split())


def composer_target(name):
    name = normalized_name(name)
    match = re.match(r'^(?:conversar em|enviar mensagem (?:em|para)|mensagem|message)\s+(.+)$', name)
    return match[1] if match else None


def discover_editors(root, discord=False):
    controls = list(root.descendants(control_type='Edit'))
    if discord:
        # Chromium can expose contenteditable through other UIA control types.
        for kind in ('Document', 'Group', 'Custom'):
            controls.extend(e for e in root.descendants(control_type=kind)
                            if composer_target(editor_name(e)))
    result, seen = [], set()
    for e in controls:
        try:
            if not (e.is_visible() and e.is_enabled() and e.is_keyboard_focusable()):
                continue
            runtime_id = tuple(e.element_info.runtime_id or ())
            key = runtime_id or ('object', id(e))
            if key not in seen:
                seen.add(key)
                result.append(e)
        except Exception:
            continue  # An element may disappear while Discord refreshes the tree.
    return result


def choose_editor(editors, expected='', discord=False):
    usable = [e for e in editors if e.is_visible() and e.is_enabled() and e.is_keyboard_focusable()]
    if expected:
        wanted = normalized_name(expected)
        target = composer_target(expected) if discord else None
        usable = [e for e in usable if normalized_name(editor_name(e)) == wanted or
                  (target is not None and composer_target(editor_name(e)) == target)]
    elif discord:
        usable = [e for e in usable if composer_target(editor_name(e))]
    if len(usable) != 1:
        if not usable:
            raise RuntimeError('Campo de mensagem não encontrado pela acessibilidade. '
                               'Abra o chat, feche pesquisas/diálogos e use Detectar campos em Perfis. '
                               'Se persistir, o cliente pode não expor o campo ao Windows.')
        raise RuntimeError('Mais de um campo de mensagem encontrado. Feche conversas laterais '
                           'ou selecione o campo em Detectar campos. Nada foi enviado.')
    return usable[0]


def read_editor_text(editor):
    # Read contents, never the accessible label (which may be a placeholder).
    for read in (lambda: editor.iface_value.CurrentValue,
                 lambda: editor.iface_text.DocumentRange.GetText(-1)):
        try:
            value = read()
            if isinstance(value, str):
                return value
        except Exception:
            pass
    raise RuntimeError('O aplicativo não permite verificar o texto desse campo. Envio cancelado.')


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
            editor = choose_editor(discover_editors(root, window['discord']),
                                   profile.get('editor_hint') or '', window['discord'])
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
            existing = read_editor_text(editor)
        except Exception as exc:
            raise RuntimeError('O aplicativo não permite verificar o rascunho desse campo. Envio cancelado.') from exc
        if existing.replace('\r', '').replace('\n', ''):
            raise RuntimeError('O chat já contém um rascunho. Limpe o campo antes do envio automático.')
        previous = pyperclip.paste()
        try:
            pyperclip.copy(message)
            check_focus()
            pg.hotkey('ctrl', 'v')
            time.sleep(.3)
            check_focus()
            if read_editor_text(editor).replace('\r\n', '\n') != message.replace('\r\n', '\n'):
                raise RuntimeError('O texto colado não pôde ser confirmado. Enter não foi enviado.')
        finally:
            if pyperclip.paste() == message:
                pyperclip.copy(previous)
    check_focus()
    pg.press('enter')
    return 'Enter enviado à janela selecionada. Recebimento da mensagem não confirmado.'
