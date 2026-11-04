import unittest
from app.automation.timing import dispatch_enter


class TimingTests(unittest.TestCase):
    def test_waits_until_boundary_without_early_enter(self):
        now = [100.8]
        presses = []
        def sleep(seconds):
            now[0] += seconds
        detail = dispatch_enter(lambda *a, **k: presses.append(now[0]), lambda: None,
                                101, lambda: now[0], sleep)
        self.assertEqual(len(presses), 1)
        self.assertGreaterEqual(presses[0], 101)
        self.assertLess(presses[0], 101.002)
        self.assertIn('atraso local', detail)

    def test_missed_deadline_does_not_press_enter(self):
        presses = []
        with self.assertRaises(RuntimeError):
            dispatch_enter(lambda *a, **k: presses.append(a), lambda: None,
                           100, lambda: 102, lambda _: None)
        self.assertEqual(presses, [])

    def test_focus_or_draft_change_cancels_wait(self):
        presses = []
        def invalid():
            raise RuntimeError('foco mudou')
        with self.assertRaises(RuntimeError):
            dispatch_enter(lambda *a, **k: presses.append(a), invalid,
                           101, lambda: 100, lambda _: None)
        self.assertEqual(presses, [])

    def test_immediate_send_does_not_wait(self):
        presses = []
        dispatch_enter(lambda *a, **k: presses.append(k), lambda: None,
                       clock=lambda: 100, sleep=lambda _: self.fail('slept'))
        self.assertEqual(presses, [{'_pause': False}])
