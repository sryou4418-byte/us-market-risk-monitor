"""AppTest server-side interaction timing; not browser paint/animation timing."""
import json
import os
from pathlib import Path
import statistics
import tempfile
import time
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from loading_service import atomic_json


def main():
    samples = {'news_to_heatmap': [], 'heatmap_to_news': [], 'news_category': []}
    with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
        root = Path(folder) / 'RiskMonitor'
        atomic_json(root / 'korean_econ_news.json', {'updated': time.time(), 'items': [
            {'title': '물가 발표', 'category': '물가', 'source': 'Test',
             'published': time.time(), 'link': 'https://example.com/news'}]})
        atomic_json(root / 'sp500_market_map_200.json', {'updated': time.time(), 'items': [
            {'symbol': 'AAPL', 'name': 'Apple', 'sector': 'Technology', 'weight': 6, 'change': 1, 'price': 100}]})
        with patch('requests.get', side_effect=AssertionError('unexpected network')) as request:
            app = AppTest.from_file(str(Path(__file__).with_name('streamlit_app.py')))
            app.query_params['view'] = 'news'
            app.run(timeout=20)
            for _ in range(10):
                for name, key in [('news_to_heatmap', 'nav_heatmap'),
                                  ('heatmap_to_news', 'nav_news'), ('news_category', 'news_filter_4')]:
                    started = time.perf_counter()
                    app.button(key=key).click().run(timeout=20)
                    samples[name].append(round((time.perf_counter() - started) * 1000, 2))
                    assert not app.exception, [e.message for e in app.exception]
            request.assert_not_called()
    result = {'scope': 'Local Streamlit AppTest interaction, warm cache, synthetic data, network mocked. '
              'Not browser click-to-paint latency, FPS, or a before/after speedup measurement.',
              'samples_per_action': 10,
              'results': {k: {'median_ms': round(statistics.median(v), 2), 'max_ms': max(v),
                              'samples_ms': v} for k, v in samples.items()}}
    Path(__file__).with_name('ui_transition_benchmark.json').write_text(
        json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
