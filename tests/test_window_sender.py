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
            e.element_info.name = name
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


class AutomaticComposerTests(unittest.TestCase):
    def editor(self, name, runtime_id=(1,)):
        e = Mock()
        e.is_visible.return_value = e.is_enabled.return_value = e.is_keyboard_focusable.return_value = True
        e.window_text.return_value = name
        e.element_info.name = name
        e.element_info.runtime_id = runtime_id
        return e

    def test_discord_selects_composer_without_selecting_search(self):
        search = self.editor('Pesquisar', (2,))
        message = self.editor('Conversar em # 〘𠗫〙𝒞onversasٍ')
        self.assertIs(choose_editor([search, message], discord=True), message)
        with self.assertRaises(RuntimeError):
            choose_editor([search], discord=True)

    def test_messletters_names_are_detected_without_manual_hint(self):
        names = ('〘𠗫〙𝒞onversasٍ', '𝕮𝖔𝖓𝖛𝖊𝖗𝖘𝖆𝖘', 'Ｃｏｎｖｅｒｓａｓ',
                 'ᴄᴏɴᴠᴇʀꜱᴀꜱ', 'C̷o̷n̷v̷e̷r̷s̷a̷s̷', '✦・𝓒𝓸𝓷𝓿𝓮𝓻𝓼𝓪𝓼・✦',
                 '⦇ 飝馫 ⦆ 𝖢𝗈𝗇𝗏𝖾𝗋𝗌𝖺𝗌', '💬┃conversas\u200b')
        for name in names:
            with self.subTest(name=name):
                message = self.editor('Conversar em # ' + name)
                self.assertIs(choose_editor([self.editor('Pesquisar', (2,)), message],
                                           discord=True), message)
                self.assertIs(choose_editor([message], 'Conversar em # ' + name, True), message)
                self.assertEqual(message.window_text(), 'Conversar em # ' + name)

    def test_distinct_channel_decorations_are_not_discarded(self):
        message = self.editor('Conversar em # ✦geral✦')
        with self.assertRaises(RuntimeError):
            choose_editor([message], 'Conversar em # ★geral★', True)

    def test_normalizes_unicode_and_localized_prefix_but_keeps_destination(self):
        message = self.editor('Mensagem # 𝒞onversas\u200b')
        self.assertIs(choose_editor([message], 'Conversar em # Conversas', True), message)
        with self.assertRaises(RuntimeError):
            choose_editor([message], 'Conversar em # Outro', True)
        with self.assertRaises(RuntimeError):
            choose_editor([message], 'Mensagem', True)

    def test_two_composers_must_not_choose_arbitrarily(self):
        a, b = self.editor('Message #general'), self.editor('Message #thread', (2,))
        with self.assertRaises(RuntimeError):
            choose_editor([a, b], discord=True)
        self.assertIs(choose_editor([a, b], 'Message #thread', True), b)

    def test_document_composer_is_discovered_and_runtime_duplicates_removed(self):
        from app.automation.window_sender import discover_editors
        search = self.editor('Pesquisar', (2,))
        composer = self.editor('Conversar em #geral')
        duplicate = self.editor('Conversar em #geral')
        page = self.editor('Discord', (3,))
        hidden = self.editor('Message #hidden', (4,))
        hidden.is_visible.return_value = False
        root = Mock()
        root.descendants.side_effect = lambda control_type: {
            'Edit': [search], 'Document': [page, composer],
            'Group': [duplicate, hidden], 'Custom': []}[control_type]
        found = discover_editors(root, True)
        self.assertEqual(found, [search, composer])
        self.assertIs(choose_editor(found, discord=True), composer)

    def test_reads_text_pattern_when_value_not_available(self):
        from app.automation.window_sender import read_editor_text
        e = Mock()
        e.iface_text.DocumentRange.GetText.return_value = 'Teste'
        self.assertEqual(read_editor_text(e), 'Teste')
        e.iface_value.CurrentValue = ''
        self.assertEqual(read_editor_text(e), '')
        e.iface_value.CurrentValue = None
        e.iface_text.DocumentRange.GetText.side_effect = RuntimeError('unsupported')
        with self.assertRaises(RuntimeError):
            read_editor_text(e)


class AccessibleLabelTests(unittest.TestCase):
    def test_empty_composer_uses_accessible_name_not_text(self):
        from app.automation.window_sender import editor_name, discover_editors
        e = Mock()
        e.element_info.name = 'Conversar em #𝕲𝖊𝖗𝖆𝖑'
        e.element_info.runtime_id = [1, 2]
        e.window_text.return_value = '\n'
        e.is_visible.return_value = e.is_enabled.return_value = e.is_keyboard_focusable.return_value = True
        root = Mock()
        root.descendants.side_effect = lambda control_type: [e] if control_type == 'Document' else []
        self.assertEqual(editor_name(e), 'Conversar em #𝕲𝖊𝖗𝖆𝖑')
        self.assertIs(choose_editor(discover_editors(root, True), discord=True), e)
        e.window_text.assert_not_called()

    def test_draft_text_cannot_impersonate_composer_label(self):
        e = Mock()
        e.element_info.name = 'Pesquisar'
        e.window_text.return_value = 'Conversar em #geral'
        with self.assertRaises(RuntimeError):
            choose_editor([e], discord=True)

    def test_missing_and_whitespace_names_are_not_menu_choices(self):
        from app.automation.window_sender import editor_name
        e = Mock()
        e.element_info.name = ' \n\u200b'
        e.iface_legacy_iaccessible.CurrentName = ''
        self.assertEqual(editor_name(e), '')
        e.iface_legacy_iaccessible.CurrentName = 'Message #general'
        self.assertEqual(editor_name(e), 'Message #general')
