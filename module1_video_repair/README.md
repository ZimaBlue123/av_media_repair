# 模块1：视频修复（module1_video_repair）

目标：尽可能把“播放器打不开”的视频修复成可播放文件，且**不覆盖原文件**。

## 常见打不开原因

- **MP4 缺少 `moov`**（索引/元数据没有写入，常见于录屏异常中断）。这种通常需要 `untrunc` 通过“同设置的正常视频”来重建。
- **`moov` 在文件末尾**（faststart 问题），可用 `ffmpeg` 重封装把 `moov` 前移。
- **封装/编码不被播放器支持**，可尝试转码或换播放器（如 VLC）。

## 使用（推荐）

在 PowerShell 里进入本模块目录：

```bash
cd "E:\Cursor Project\av_media_repair\module1_video_repair"
```

### 0) 安装（可选）

本模块**零第三方 Python 依赖**。建议用 Python 3.9+ 运行。

```bash
python -m pip install -e .
```

### 1) 诊断文件（是否缺少 moov）

```bash
python -m video_repair.cli probe "E:\Cursor Project\录屏1-20260401.mp4"
```

### 2) 尝试用 ffmpeg 无损重封装（适用于 moov 在末尾）

> 需要你已安装 `ffmpeg`，并且 `ffmpeg.exe` 在 PATH 中。

```bash
python -m video_repair.cli remux "E:\Cursor Project\input.mp4" -o "E:\Cursor Project\output_remux.mp4"
```

### 3) 用 untrunc 修复（适用于缺少 moov）

> 需要：
> - 一个“同录屏设置”的正常样本视频 `good.mp4`（几秒即可）
> - `untrunc.exe`（本项目在 Windows 下可自动下载并缓存到 `module1_video_repair/tools/`）

```bash
python -m video_repair.cli untrunc "E:\Cursor Project\good.mp4" "E:\Cursor Project\录屏1-20260401.mp4" -o "E:\Cursor Project\output_fixed.mp4" --untrunc "C:\path\to\untrunc.exe"
```

### 4) 方案 B（成功率高）：批量用“正常同设置视频”重建 moov

你当前目录约定：

- 异常视频：`module1_video_repair/input/`
- 正常视频：`module1_video_repair/template/`
- 输出目录：`module1_video_repair/output/`

一键批量修复 + 自检（会写出 JSON 报告）：

```bash
python -m video_repair.cli batch-untrunc `
  --input-dir "E:\Cursor Project\av_media_repair\module1_video_repair\input" `
  --template-dir "E:\Cursor Project\av_media_repair\module1_video_repair\template" `
  --output-dir "E:\Cursor Project\av_media_repair\module1_video_repair\output" `
  --report "E:\Cursor Project\av_media_repair\module1_video_repair\output\report.json"
```

如果修复后“能打开但画面扭曲/花屏/部分播放器无声”，启用**强兜底重编码**（耗时长，但兼容性最好）：

```bash
python -m video_repair.cli batch-untrunc `
  --input-dir "E:\Cursor Project\av_media_repair\module1_video_repair\input" `
  --template-dir "E:\Cursor Project\av_media_repair\module1_video_repair\template" `
  --output-dir "E:\Cursor Project\av_media_repair\module1_video_repair\output" `
  --report "E:\Cursor Project\av_media_repair\module1_video_repair\output\report.json" `
  --reencode-video
```

说明：

- `template` 目录里如有多个视频，工具会自动挑选**最大**的一个作为样本。
- Windows 下若本机没装 `untrunc/ffprobe`，会尝试从 GitHub Releases 下载并缓存到 `module1_video_repair/tools/`（下次复用）。

## 安全建议

- 永远对原始文件做备份/只读处理
- 输出文件使用新文件名（本工具默认如此）

