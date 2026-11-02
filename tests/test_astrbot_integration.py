import importlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    module = importlib.import_module('astrbot_plugin_see_now.main')
    from astrbot.api.message_components import Video
except ImportError:
    module = None


@unittest.skipUnless(module, 'AstrBot library unavailable')
class ActualAstrBotEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_video_command_runs_before_existing_video_handler(self):
        from astrbot.core.star.star_handler import star_handlers_registry
        handlers = [h for h in star_handlers_registry._handlers
                    if h.handler is module.Main.see_attached_video]
        self.assertEqual(len(handlers), 1)
        self.assertGreater(handlers[0].extras_configs['priority'], 1200)

    async def test_attached_command_uses_video_component(self):
        class Event:
            def is_admin(self): return True
            def is_private_chat(self): return True
            def get_messages(self): return [Video(file='https://example.com/v.mp4')]
            def plain_result(self, text): return text
            def stop_event(self): self.stopped = True
        plugin = object.__new__(module.Main)
        plugin.config = {}
        plugin._analyze = AsyncMock(return_value='visual result')
        async def download(url, dest, max_bytes):
            dest.write_bytes(b'video')
            return dest
        event = Event()
        with patch.object(module, 'download_video', download):
            replies = [item async for item in plugin.see_attached_video(event)]
        self.assertEqual(replies, ['visual result'])
        self.assertTrue(event.stopped)
        plugin._analyze.assert_awaited_once()

    async def test_nonadmin_cannot_trigger_analysis(self):
        event = SimpleNamespace(is_admin=lambda: False, is_private_chat=lambda: True, plain_result=lambda x: x, stop_event=lambda: None)
        plugin = object.__new__(module.Main)
        replies = [item async for item in plugin.see_attached_video(event)]
        self.assertIn('管理员', replies[0])
