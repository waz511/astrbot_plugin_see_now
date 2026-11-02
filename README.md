# See Now 视频分析（AstrBot 插件）

使用 [dsh-see-now](https://github.com/SAOS-3624/dsh-see-now) 的原始画面变化筛帧和拼图算法，让 AstrBot 视觉模型按时间顺序分析视频画面。插件是独立的，不自动替换原有视频插件。理解效果和费用取决于视频、拼图数量和视觉模型，尚未完成真实视频与原方案的效果和费用对照。

## 安装与配置

需要 AstrBot、Node.js 20 或更高版本、FFmpeg 和支持图片输入的模型服务。将插件目录安装到 AstrBot 的 `data/plugins`，重启或在插件管理中加载；在插件配置中设置视觉服务 ID，留空时使用当前会话服务。Windows 上若 PATH 中的 `ffmpeg` 是 `.cmd` 包装脚本，请将 `ffmpeg_path` 设置为实际 `ffmpeg.exe` 路径。筛帧核心已包含在插件中，无需 npm install。

管理员私聊可使用：

- `/看视频` 与一个视频附件放在同一条消息。需要平台提供可访问的 HTTPS 地址或允许目录内的本地文件；引用和转发暂不支持，附件下载不跟随重定向。
- `/看本地视频 文件名`：先在插件配置中设置允许读取的视频目录，文件必须位于该目录。

命令前缀取决于 AstrBot 的唤醒前缀设置：如果未配置 `/` 前缀，可直接发送 `看视频` 或 `看本地视频 文件名`。

插件默认限制文件大小、处理时长和拼图数量，达到上限会提示只分析了部分内容；请求会将拼图发送给所选视觉模型服务，请据此选择服务。当前只分析画面，不处理音频或字幕。附件入口与其他插件共存的实际事件顺序依平台和安装环境而异，首次使用应验证。

## 许可与来源

`bridge/vendor/` 包含 SAOS-3624 的 dsh-see-now 源码，来源、固定版本和许可证见 [UPSTREAM.md](bridge/vendor/UPSTREAM.md)、[LICENSE](bridge/vendor/LICENSE) 和 [NOTICE](bridge/vendor/NOTICE)。上游主体使用 PolyForm Noncommercial License 1.0.0，商业使用须另行取得授权；本项目不得将上游代码误标为 MIT 或 Apache-2.0。上游筛帧模块以原样保留，其他代码为接口适配。

## 测试

```sh
python -m unittest discover -s tests
node --test bridge/test/*.test.mjs
```

测试不自动向模型发送视频；真实识别效果、耗时和费用需要在自己的环境中单独验证。
