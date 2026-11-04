"""Dois metodos: UIA quando suportado; mouse apenas com permissao explicita."""
import sys
import time


def _coordinates(profile, key):
    x, y = profile.get(key + '_x'), profile.get(key + '_y')
    if x is None or y is None:
        raise RuntimeError(f'Marque o ponto "{key}" no perfil antes de executar.')
    return int(x), int(y)


def _window_for_point(x, y, expected_title=''):
    import win32gui
    import win32con
    hwnd = win32gui.WindowFromPoint((x, y))
    if not hwnd:
        raise RuntimeError('Nenhuma janela encontrada na coordenada configurada.')
    root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
    title = win32gui.GetWindowText(root)
    if not title or (expected_title and expected_title.casefold() not in title.casefold()):
        raise RuntimeError('O aplicativo de destino não está na posição marcada. '
                           f'Janela encontrada: {title!r}. Esperada: {expected_title!r}.')
    if win32gui.IsIconic(root):
        raise RuntimeError('A janela de destino está minimizada.')
    return root


def _uia(profile, message, mode):
    if sys.platform != 'win32':
        raise RuntimeError('A automação UIA requer Windows.')
    from pywinauto import Desktop
    hint = (profile.get('app_hint') or '').strip()
    send_x, send_y = _coordinates(profile, 'send')
    send_root = _window_for_point(send_x, send_y, hint)
    desktop = Desktop(backend='uia')
    if mode == 'write':
        field_x, field_y = _coordinates(profile, 'message')
        if _window_for_point(field_x, field_y, hint) != send_root:
            raise RuntimeError('Os pontos pertencem a janelas diferentes.')
        try:
            desktop.from_point(field_x, field_y).set_edit_text(message)
        except Exception as ex:
            raise RuntimeError('O campo não permite escrever em segundo plano por UI Automation.') from ex
    try:
        desktop.from_point(send_x, send_y).invoke()
    except Exception as ex:
        raise RuntimeError('O botão não permite a ação Invoke do Windows UI Automation.') from ex
    return 'Ação solicitada via UI Automation. Entrega não confirmada.'


def _mouse(profile, message, mode):
    if sys.platform != 'win32':
        raise RuntimeError('O envio por mouse requer Windows.')
    import pyautogui as pg
    import pyperclip
    import win32gui
    hint = (profile.get('app_hint') or '').strip()
    x, y = _coordinates(profile, 'send')
    root = _window_for_point(x, y, hint)
    if mode == 'write':
        cx, cy = _coordinates(profile, 'message')
        if _window_for_point(cx, cy, hint) != root:
            raise RuntimeError('O campo e o botão de envio estão em janelas diferentes.')
    try:
        win32gui.SetForegroundWindow(root)
    except Exception as ex:
        raise RuntimeError('O Windows não permitiu ativar a janela do aplicativo.') from ex
    time.sleep(0.35)
    if mode == 'write':
        # Revalida antes de escrever, evitando enviar texto a janela errada.
        if _window_for_point(cx, cy, hint) != root:
            raise RuntimeError('A janela mudou antes da digitação. Envio cancelado.')
        pg.click(cx, cy)
        pyperclip.copy(message)
        pg.hotkey('ctrl', 'v')
        time.sleep(0.25)
    if _window_for_point(x, y, hint) != root:
        raise RuntimeError('O botão mudou de lugar. Clique cancelado para evitar envio incorreto.')
    pg.click(x, y)
    return 'Clique realizado com mouse. Entrega não confirmada.'


def send(profile, message, mode):
    if mode not in ('write', 'click'):
        raise ValueError('Modo de envio inválido.')
    if mode == 'write' and not (message or '').strip():
        raise ValueError('Mensagem vazia.')
    provider = profile.get('provider') or 'auto'
    if provider == 'window':
        from app.automation.window_sender import send_window
        return send_window(profile, message, mode)
    foreground_allowed = bool(profile.get('allow_foreground'))
    if provider in ('auto', 'uia'):
        try:
            return _uia(profile, message, mode)
        except Exception as error:
            if provider == 'uia' or not foreground_allowed:
                raise
            return _mouse(profile, message, mode) + ' UIA indisponível: ' + str(error)
    if provider == 'coords':
        if not foreground_allowed:
            raise RuntimeError('Uso do mouse não autorizado neste perfil.')
        return _mouse(profile, message, mode)
    raise RuntimeError('Método desconhecido.')
