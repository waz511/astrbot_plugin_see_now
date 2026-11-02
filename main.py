import asyncio
import tempfile
from pathlib import Path

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Video
from astrbot.api.star import Context, Star
from .service import resolve_video, extract, analyze_sheets, download_video


class Main(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.config = config
        self._lock = asyncio.Lock()

    @filter.command('看本地视频', priority=1300)
    async def see_local_video(self, event: AstrMessageEvent, filename: str):
        """管理员私聊分析允许目录中的本地视频：/看本地视频 文件名"""
        if not event.is_admin() or not event.is_private_chat():
            yield event.plain_result('此命令仅限管理员私聊使用。')
            event.stop_event()
            return
        root = str(self.config.get('video_root', '')).strip()
        if not root:
            yield event.plain_result('请先在插件设置中配置允许读取的视频目录。')
            event.stop_event()
            return
        try:
            video = resolve_video(root, filename)
            max_mb = max(1, min(int(self.config.get('max_file_mb', 500)), 2048))
            if video.stat().st_size > max_mb * 1024 * 1024:
                raise ValueError('视频文件超过设置的大小限制')
            answer = await self._analyze(event, video)
            yield event.plain_result(answer)
        except (ValueError, OSError, RuntimeError, asyncio.TimeoutError):
            yield event.plain_result('视频分析失败：请检查允许目录、视频文件、Node/FFmpeg、模型支持与处理限额。Windows 请将 ffmpeg_path 指向 ffmpeg.exe。')
        event.stop_event()

    @filter.command('看视频', priority=1300)
    async def see_attached_video(self, event: AstrMessageEvent):
        """管理员私聊：命令和一个视频附件放在同一条消息中。"""
        if not event.is_admin() or not event.is_private_chat():
            yield event.plain_result('此命令仅限管理员私聊使用。')
            event.stop_event()
            return
        videos = [item for item in event.get_messages() if isinstance(item, Video)]
        if len(videos) != 1:
            yield event.plain_result('请在同一条消息中附带一个视频。引用和转发视频暂不支持。')
            event.stop_event()
            return
        try:
            component = videos[0]
            url = next((x for x in (component.url, component.file) if isinstance(x, str) and x.startswith('https://')), '')
            max_mb = max(1, min(int(self.config.get('max_file_mb', 500)), 2048))
            with tempfile.TemporaryDirectory(prefix='astrbot-see-now-input-') as tmp:
                if url:
                    video = await download_video(url, Path(tmp) / 'video.mp4', max_mb * 1024 * 1024)
                else:
                    root = str(self.config.get('video_root', '')).strip()
                    if not root:
                        raise ValueError('没有可用的 HTTPS 附件地址')
                    video = resolve_video(root, component.path or component.file)
                    if video.stat().st_size > max_mb * 1024 * 1024:
                        raise ValueError('视频超过大小限制')
                answer = await self._analyze(event, video)
            yield event.plain_result(answer)
        except Exception:
            yield event.plain_result('视频分析失败：附件可能不可下载、超过限额，或视觉服务及依赖未配置。当前不跟随下载重定向；Windows 请将 ffmpeg_path 指向 ffmpeg.exe。')
        event.stop_event()

    async def _analyze(self, event, video):
            provider_id = str(self.config.get('vision_provider_id', '')).strip()
            provider = self.context.get_provider_by_id(provider_id) if provider_id else self.context.get_using_provider(event.unified_msg_origin)
            if not provider:
                raise ValueError('未找到视觉模型服务，请在插件设置中指定服务 ID')
            max_sheets = max(1, min(int(self.config.get('max_sheets', 20)), 40))
            max_seconds = max(1, min(int(self.config.get('max_seconds', 600)), 3600))
            timeout = max(30, min(int(self.config.get('timeout_seconds', 300)), 1800))
            async with self._lock:
                with tempfile.TemporaryDirectory(prefix='astrbot-see-now-') as tmp:
                    sheets, truncated = await extract(video, Path(tmp), str(self.config.get('node_path', 'node')), str(self.config.get('ffmpeg_path', '')).strip(), max_seconds, max_sheets, timeout)
                    answer = await asyncio.wait_for(analyze_sheets(provider, sheets), timeout=timeout)
            prefix = '注意：视频达到处理上限，仅分析了部分内容。\n' if truncated else ''
            return prefix + answer
