import unittest
from streamlit.testing.v1 import AppTest
class TestStreamlit(unittest.TestCase):
    def test_market_screen(self):
        app=AppTest.from_string('''import streamlit as st
from market_view import render
from test_market import fixture
st.set_page_config(layout="wide")
render(st,fixture(),"2026-09-05")
''').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.expander),38)
        self.assertEqual(len(app.subheader),8)
