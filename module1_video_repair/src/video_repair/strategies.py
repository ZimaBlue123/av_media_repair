from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecResult:
    ok: bool
    command: list[str]
    stdout: str
    stderr: str
    returncode: int


def _run(command: list[str]) -> ExecResult:
    # 某些第三方可执行文件在 Windows 下会输出非 UTF-8 文本；
    # 这里用 errors='replace' 避免解码异常导致子进程输出读取线程崩溃。
    p = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ExecResult(
        ok=(p.returncode == 0),
        command=command,
        stdout=p.stdout or "",
        stderr=p.stderr or "",
        returncode=p.returncode,
    )


def sanitize_container_with_ffmpeg(
    input_path: str | Path,
    output_path: str | Path,
    *,
    ffmpeg: str | None = None,
) -> ExecResult:
    """
    用 ffmpeg 重新写 MP4 封装（尽量无损 copy），提升播放器兼容性：
    - 生成时间戳（genpts）
    - moov 前移（faststart）
    """
    in_p = str(Path(input_path))
    out_p = str(Path(output_path))
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        return ExecResult(
            ok=False,
            command=["ffmpeg"],
            stdout="",
            stderr="未找到 ffmpeg。请先安装 ffmpeg，并确保 ffmpeg.exe 在 PATH 中，或传入 --ffmpeg 参数。",
            returncode=127,
        )

    cmd = [
        exe,
        "-y",
        "-fflags",
        "+genpts",
        "-i",
        in_p,
        "-map",
        "0",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        out_p,
    ]
    return _run(cmd)


def sanitize_audio_with_ffmpeg(
    input_path: str | Path,
    output_path: str | Path,
    *,
    ffmpeg: str | None = None,
) -> ExecResult:
    """
    若 copy 封装后仍无声，可尝试重编码音频（视频仍 copy）。
    """
    in_p = str(Path(input_path))
    out_p = str(Path(output_path))
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        return ExecResult(
            ok=False,
            command=["ffmpeg"],
            stdout="",
            stderr="未找到 ffmpeg。请先安装 ffmpeg，并确保 ffmpeg.exe 在 PATH 中，或传入 --ffmpeg 参数。",
            returncode=127,
        )

    cmd = [
        exe,
        "-y",
        "-fflags",
        "+genpts",
        "-i",
        in_p,
        "-map",
        "0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        out_p,
    ]
    return _run(cmd)


def reencode_av_with_ffmpeg(
    input_path: str | Path,
    output_path: str | Path,
    *,
    ffmpeg: str | None = None,
) -> ExecResult:
    """
    通过重新编码视频+音频来“重建码流”（最强兜底，耗时长）。
    - 视频：libopenh264（本项目内置 ffmpeg build 通常可用）
    - 音频：AAC
    """
    in_p = str(Path(input_path))
    out_p = str(Path(output_path))
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        return ExecResult(
            ok=False,
            command=["ffmpeg"],
            stdout="",
            stderr="未找到 ffmpeg。请先安装 ffmpeg，并确保 ffmpeg.exe 在 PATH 中，或传入 --ffmpeg 参数。",
            returncode=127,
        )

    cmd = [
        exe,
        "-y",
        "-hide_banner",
        "-v",
        "error",
        # 对损坏码流更鲁棒：丢弃坏包 + 忽略解码错误（可能丢帧，但能去花屏）
        "-fflags",
        "+genpts+discardcorrupt",
        "-err_detect",
        "ignore_err",
        "-i",
        in_p,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libopenh264",
        "-pix_fmt",
        "yuv420p",
        "-g",
        "60",
        "-keyint_min",
        "60",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-af",
        "aresample=async=1:first_pts=0",
        "-movflags",
        "+faststart",
        out_p,
    ]
    return _run(cmd)


def remux_with_ffmpeg(input_path: str | Path, output_path: str | Path, *, ffmpeg: str | None = None) -> ExecResult:
    in_p = str(Path(input_path))
    out_p = str(Path(output_path))
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        return ExecResult(
            ok=False,
            command=["ffmpeg"],
            stdout="",
            stderr="未找到 ffmpeg。请先安装 ffmpeg，并确保 ffmpeg.exe 在 PATH 中，或传入 --ffmpeg 参数。",
            returncode=127,
        )

    # -movflags +faststart: 把 moov 前移（如果存在的话）
    # -c copy: 尽量无损重封装
    cmd = [exe, "-y", "-i", in_p, "-c", "copy", "-movflags", "+faststart", out_p]
    return _run(cmd)


def repair_with_untrunc(
    good_path: str | Path,
    broken_path: str | Path,
    output_path: str | Path,
    *,
    untrunc: str | None = None,
) -> ExecResult:
    good_p = str(Path(good_path))
    broken_p = str(Path(broken_path))
    out_p = str(Path(output_path))
    exe = untrunc or shutil.which("untrunc") or shutil.which("untrunc.exe")
    if not exe:
        return ExecResult(
            ok=False,
            command=["untrunc"],
            stdout="",
            stderr="未找到 untrunc。请下载 untrunc.exe 并通过 --untrunc 指定路径，或把它加入 PATH。",
            returncode=127,
        )

    # untrunc 默认会输出到当前目录/或生成新文件名，各版本行为略有不同
    # 这里用工作目录 + 复制结果的方式，保证输出路径可控。
    out_dir = Path(out_p).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [exe, good_p, broken_p]
    t_before = Path(broken_p).stat().st_mtime if Path(broken_p).exists() else None
    r = _run(cmd)
    if not r.ok:
        return r

    # 尝试在 broken 文件同目录找到 untrunc 输出（常见：<broken>_fixed.mp4 或 fixed_<broken>）
    candidates = []
    broken_name = Path(broken_p).name
    for pat in (
        f"{Path(broken_p).stem}_fixed{Path(broken_p).suffix}",
        f"fixed_{broken_name}",
        f"repaired_{broken_name}",
        f"{broken_name}_fixed.mp4",
    ):
        candidates.append(Path.cwd() / pat)
        candidates.append(Path(broken_p).with_name(pat))

    produced = next((c for c in candidates if c.exists() and c.stat().st_size > 0), None)
    if not produced:
        # 兜底：在坏文件目录中找最新的 *fixed*.mp4
        bdir = Path(broken_p).parent
        fixed = sorted(
            [p for p in bdir.glob("*fixed*.mp4") if p.is_file() and p.stat().st_size > 0],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        # 若能拿到执行前时间，用它过滤掉更早的文件
        if t_before is not None:
            fixed = [p for p in fixed if p.stat().st_mtime >= t_before]
        produced = fixed[0] if fixed else None
    if not produced:
        return ExecResult(
            ok=False,
            command=cmd,
            stdout=r.stdout,
            stderr=(r.stderr + "\n" if r.stderr else "")
            + "untrunc 执行成功但未找到输出文件（不同版本输出命名可能不同）。请在命令执行目录和坏文件目录手动查找 *fixed*.mp4。",
            returncode=2,
        )

    try:
        Path(out_p).write_bytes(produced.read_bytes())
    except Exception as e:  # noqa: BLE001
        return ExecResult(
            ok=False,
            command=cmd,
            stdout=r.stdout,
            stderr=(r.stderr + "\n" if r.stderr else "") + f"复制输出到目标路径失败：{e}",
            returncode=3,
        )

    return ExecResult(ok=True, command=cmd, stdout=r.stdout, stderr=r.stderr, returncode=0)

