import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from loading_service import atomic_json

APP = Path(__file__).resolve().parents[1] / 'streamlit_app.py'


class NavigationTests(unittest.TestCase):
    def test_news_heatmap_roundtrip_preserves_session_category_and_theme(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            root = Path(folder) / 'RiskMonitor'
            atomic_json(root / 'korean_econ_news.json', {'updated': time.time(), 'items': [
                {'title': '물가 발표', 'category': '물가', 'source': 'Test',
                 'published': time.time(), 'link': 'https://example.com/news'},
                {'title': '연준 발표', 'category': '연준·금리', 'source': 'Test',
                 'published': time.time(), 'link': 'https://example.com/fed'}]})
            atomic_json(root / 'sp500_market_map_200.json', {'updated': time.time(), 'items': [
                {'symbol': 'AAPL', 'name': 'Apple', 'sector': 'Technology',
                 'weight': 6, 'change': 1, 'price': 100}]})
            with patch('requests.get', side_effect=AssertionError('unexpected network')) as request:
                app = AppTest.from_file(str(APP))
                app.query_params['view'] = 'news'
                app.run(timeout=20)
                app.session_state['_test_session_marker'] = 'preserved'
                buttons = {b.key: b for b in app.button}
                self.assertEqual({b.label for b in app.sidebar.button if b.key.startswith('nav_')},
                                 {'대시보드','S&P500 시장 맵','위험지수','시장 상태','뉴스'})
                category = next(b for b in app.button if b.label.startswith('물가 ·'))
                app.button(key=category.key).click().run(timeout=20)
                self.assertEqual(app.query_params['news_category'], ['물가'])
                text = '\n'.join(m.value for m in app.markdown)
                self.assertIn('물가 발표', text)
                self.assertNotIn('연준 발표', text)
                app.button(key='theme_toggle').click().run(timeout=20)
                self.assertEqual(app.query_params['theme'], ['dark'])
                app.button(key='nav_heatmap').click().run(timeout=20)
                self.assertEqual(app.query_params['view'], ['heatmap'])
                self.assertTrue(any('AAPL' in m.value for m in app.markdown))
                app.button(key='nav_news').click().run(timeout=20)
                self.assertEqual(app.query_params['view'], ['news'])
                self.assertEqual(app.query_params['news_category'], ['물가'])
                self.assertEqual(app.query_params['theme'], ['dark'])
                self.assertEqual(app.session_state['_test_session_marker'], 'preserved')
                self.assertFalse(app.exception, [x.message for x in app.exception])
                request.assert_not_called()

    def test_refresh_is_one_shot_and_navigation_clears_it(self):
        app = AppTest.from_string('''import streamlit as st
from ui_shell import render_shell
st.set_page_config(layout="wide")
render_shell(st.query_params.get('view','dashboard'), st.query_params.get('theme','light'))
''').run(timeout=15)
        app.button(key='data_refresh').click().run(timeout=15)
        self.assertEqual(app.query_params['refresh'], ['1'])
        app.button(key='nav_market').click().run(timeout=15)
        self.assertNotIn('refresh', app.query_params)
        self.assertEqual(app.query_params['view'], ['market'])
