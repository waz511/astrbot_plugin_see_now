import asyncio
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from service import resolve_video, validate_result, analyze_sheets, validate_media_url, extract


class TestService(unittest.TestCase):
    def test_child_timeout_precedes_parent(self):
        class Proc:
            returncode = 0
            async def communicate(self): return b'{"sheets":[{"file":"x.png"}]}', b''
        async def run(root):
            (root / 'x.png').write_bytes(b'x')
            captured = []
            async def spawn(*args, **kwargs):
                captured.extend(args)
                return Proc()
            with patch('asyncio.create_subprocess_exec', spawn), patch('shutil.which', return_value=None):
                await extract(root / 'video.mp4', root, 'node', '', 60, 3, 30)
            self.assertEqual(captured[captured.index('--timeout-ms') + 1], '25000')
        with tempfile.TemporaryDirectory() as d:
            asyncio.run(run(Path(d)))
    def test_remote_sources_only_https_without_userinfo_or_private_ip(self):
        for value in ('http://example.com/a', 'https://localhost/a', 'https://127.0.0.1/a', 'https://user:pass@example.com/a', 'file:///x'):
            with self.assertRaises(ValueError): validate_media_url(value)
        self.assertEqual(validate_media_url('https://example.com/video'), 'https://example.com/video')
    def test_paths_are_confined(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'ok.mp4').write_bytes(b'x')
            self.assertEqual(resolve_video(root, 'ok.mp4'), (root / 'ok.mp4').resolve())
            for p in ('../secret.mp4', 'missing.mp4', 'a.txt'):
                with self.assertRaises(ValueError):
                    resolve_video(root, p)

    def test_bridge_result_cannot_escape_or_exceed_limit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'one.png').write_bytes(b'png')
            self.assertEqual(len(validate_result({'sheets': [{'file': 'one.png', 'from': 0, 'to': 1}]}, root, 2)), 1)
            for data in ({'sheets': [{'file': '../outside.png'}]}, {'sheets': []}, {'sheets': [{'file': 'one.png'}] * 3}):
                with self.assertRaises(ValueError):
                    validate_result(data, root, 2)

    def test_all_sheets_are_analyzed_in_order(self):
        class Provider:
            def __init__(self): self.calls = []
            async def text_chat(self, **kwargs):
                self.calls.append(kwargs)
                return type('Response', (), {'completion_text': f'part {len(self.calls)}'})()
        p = Provider()
        items = [(Path(f'{n}.png'), n, n + 1) for n in range(5)]
        result = asyncio.run(analyze_sheets(p, items, batch_size=2))
        self.assertEqual([len(c['image_urls']) for c in p.calls], [2, 2, 1])
        self.assertIn('part 3', result)
