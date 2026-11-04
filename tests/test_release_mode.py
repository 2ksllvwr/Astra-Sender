import unittest
import time
from unittest.mock import Mock, patch
from app.automation.window_sender import wait_available, FieldUnavailable, validate, _send


class ReleaseTests(unittest.TestCase):
    def test_waits_through_locked_field_then_returns(self):
        now = [0.0]
        expected = object()
        def find():
            if now[0] < .15:
                raise FieldUnavailable('locked')
            return expected
        self.assertIs(wait_available(find, lambda: None, 1, lambda: now[0],
                                     lambda n: now.__setitem__(0, now[0] + n)), expected)
        self.assertLess(now[0], .21)

    def test_timeout_and_ambiguity_are_not_silent_retries(self):
        now = [0.0]
        find = Mock(side_effect=FieldUnavailable('locked'))
        with self.assertRaises(TimeoutError):
            wait_available(find, lambda: None, .1, lambda: now[0],
                           lambda n: now.__setitem__(0, now[0] + n))
        with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
            wait_available(Mock(side_effect=RuntimeError('ambiguous')), lambda: None, 1)

    def test_release_requires_named_destination_and_write_for_repetitions(self):
        p = dict(window_process='Discord.exe', allow_foreground=True, wait_release=True,
                 send_count=3)
        with self.assertRaises(ValueError):
            validate(p, 'write', 'Oi')
        p['editor_hint'] = 'Conversar em #geral'
        validate(p, 'configure', '')
        validate(p, 'write', 'Oi')
        with self.assertRaises(ValueError):
            validate(p, 'click', '')

    def run_sender(self, count, clear=True, release=True):
        # Exercise the actual paste/Enter loop, without sending outside the test.
        pg, clipboard, gui, desktop = Mock(), Mock(), Mock(), Mock()
        editor = Mock()
        editor.element_info.name = 'Conversar em #geral'
        editor.iface_value.CurrentIsReadOnly = False
        editor.iface_value.CurrentValue = ''
        editor.has_keyboard_focus.return_value = True
        editor.is_visible.return_value = editor.is_enabled.return_value = editor.is_keyboard_focusable.return_value = True
        root = desktop.return_value.window.return_value.wrapper_object.return_value
        root.descendants.return_value = [editor]
        gui.GetForegroundWindow.return_value = 123
        gui.IsIconic.return_value = False
        clip = ['anterior']
        clipboard.paste.side_effect = lambda: clip[0]
        clipboard.copy.side_effect = lambda x: clip.__setitem__(0, x)
        pg.hotkey.side_effect = lambda *args, **kw: setattr(editor.iface_value, 'CurrentValue', clip[0]) if args == ('ctrl', 'v') else None
        def press(*args, **kwargs):
            if clear:
                editor.iface_value.CurrentValue = ''
        pg.press.side_effect = press
        modules = dict(win32con=Mock(), win32gui=gui, pyautogui=pg, pyperclip=clipboard,
                       pywinauto=Mock(Desktop=desktop))
        profile = dict(window_process='Discord.exe', window_title='Discord', editor_hint=editor.element_info.name,
                       send_count=count, wait_release=release)
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.dict('sys.modules', modules))
            stack.enter_context(patch('app.automation.window_sender.list_windows', return_value=[dict(hwnd=123, process='Discord.exe', title='Discord', discord=True)]))
            if not clear:
                # Reject only the second message's wait-for-empty check.
                from app.automation.window_sender import wait_text
                stack.enter_context(patch('app.automation.window_sender.wait_text', side_effect=lambda e, text, check, **kw: (_ for _ in ()).throw(RuntimeError('not cleared')) if text == '' else wait_text(e, text, check)))
            try:
                result = _send(profile, 'Oi', 'write', target=time.time() - 2 if release else None)
            except Exception as exc:
                result = str(exc)
        self.assertEqual(clip[0], 'anterior')
        return pg, result

    def test_three_separate_pastes_and_enters(self):
        pg, result = self.run_sender(3, release=False)
        self.assertEqual(pg.press.call_count, 3)
        self.assertIn('3/3', result)

    def test_no_second_enter_if_field_does_not_clear(self):
        pg, result = self.run_sender(3, clear=False, release=False)
        self.assertEqual(pg.press.call_count, 1)
        self.assertIn('1/3', result)

    def test_release_can_send_after_old_one_second_cutoff(self):
        pg, result = self.run_sender(1, release=True)
        self.assertEqual(pg.press.call_count, 1)
        self.assertIn('1/1', result)
