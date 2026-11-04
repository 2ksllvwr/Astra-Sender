import unittest
from unittest.mock import Mock
from app.automation.window_sender import discord_route, resolve_window, choose_editor, validate


class WindowSenderTests(unittest.TestCase):
    def test_discord_links(self):
        self.assertEqual(discord_route('https://discord.com/channels/@me/123/456'), 'discord://-/channels/@me/123')
        for link in ('https://evil.com/channels/1/2', 'https://discord.com.evil.com/channels/1/2',
                     'file:///channels/1/2', 'https://discord.com/channels/1/2?x=1', 'https://discord.com/channels/1'):
            with self.assertRaises(ValueError):
                discord_route(link)

    def test_exact_process_and_title(self):
        p = dict(window_process='C:/App/app.exe', window_title='Chat A')
        a = dict(process='C:/App/app.exe', title='Chat A', discord=False)
        b = dict(process='C:/App/app.exe', title='Chat B', discord=False)
        self.assertEqual(resolve_window(p, [a,b]), a)
        with self.assertRaises(RuntimeError):
            resolve_window(p, [b])
        with self.assertRaises(RuntimeError):
            resolve_window(p, [a,a])

    def test_discord_dynamic_title_only_when_unique(self):
        p = dict(window_process='discord.exe', window_title='Old')
        w = dict(process='discord.exe', title='New', discord=True)
        self.assertEqual(resolve_window(p, [w]), w)
        with self.assertRaises(RuntimeError):
            resolve_window(p, [w,w])

    def test_ambiguous_editor_aborts(self):
        def editor(name):
            e = Mock()
            e.is_visible.return_value = e.is_enabled.return_value = e.is_keyboard_focusable.return_value = True
            e.window_text.return_value = name
            return e
        search, message = editor('Pesquisar'), editor('Mensagem #geral')
        self.assertIs(choose_editor([search,message], 'Mensagem #geral'), message)
        with self.assertRaises(RuntimeError):
            choose_editor([search,message])
        with self.assertRaises(RuntimeError):
            choose_editor([search,message], 'Mensagem #outro')

    def test_enter_needs_no_coordinates_but_requires_permission(self):
        p = dict(window_process='app.exe', allow_foreground=True)
        validate(p, 'write', 'Teste')
        with self.assertRaises(ValueError):
            validate(dict(p, allow_foreground=False), 'write', 'Teste')
        with self.assertRaises(ValueError):
            validate(p, 'write', '')

    def test_discord_link_needs_destination_hint(self):
        p = dict(window_process='C:\\Discord\\Discord.exe', allow_foreground=True,
                 chat_url='https://discord.com/channels/1/2')
        with self.assertRaises(ValueError):
            validate(p, 'write', 'Teste')
        validate(dict(p, editor_hint='Mensagem #geral'), 'write', 'Teste')
