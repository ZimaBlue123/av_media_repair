# av_media_repair

用于**修复视频**与**处理音视频文件**的工具项目（Windows 优先）。

## 模块

- `module1_video_repair/`：模块1（视频修复）

## 快速开始（方案：untrunc 重建 moov）

当 MP4 因异常中断导致缺少 `moov`（索引/元数据）时，成功率较高的办法是：准备一个“同录制设置”的正常样本视频，然后用 `untrunc` 重建。

本仓库已在 `module1_video_repair/` 内提供批量脚本，详见 `module1_video_repair/README.md` 的 `batch-untrunc`。

