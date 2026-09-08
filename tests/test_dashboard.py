import unittest

from dashboard_view import overview_html


class DashboardTests(unittest.TestCase):
    def test_engine_state_is_preserved_even_with_two_rapid_signals(self):
        rendered = overview_html(55.0, '보통', '+1.0',
                                 {'level': '관찰', 'count': 1},
                                 {'level': '관찰', 'count': 2}, '2026-09-04')
        self.assertIn('시장 급변신호', rendered)
        self.assertIn('감지된 신호 2개', rendered)
        self.assertNotIn('급변 경보', rendered)
        self.assertNotIn('home-state alert', rendered)
        self.assertEqual(rendered.count(' / 100'), 1)

    def test_missing_score_and_states_are_not_normal_or_zero(self):
        rendered = overview_html(float('nan'), '낮음', '0', {}, {}, '확인 불가')
        self.assertIn('데이터 부족', rendered)
        self.assertIn('신호 수 확인 불가', rendered)
        self.assertNotIn('정상', rendered)
        self.assertNotIn('nan', rendered)
        self.assertNotIn('감지된 신호 0개', rendered)

    def test_external_text_is_escaped(self):
        rendered = overview_html(70, '높음', '<img src=x>',
                                 {'level': '<script>', 'count': 1}, {}, '<b>date</b>')
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<img', rendered)
        self.assertIn('&lt;b&gt;date&lt;/b&gt;', rendered)
