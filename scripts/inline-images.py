#!/usr/bin/env python3
"""inline-images.py — 把 HTML 里的本地图片转成 base64 data URI 内嵌。

支持三种图来源：
  1. baoyu 渲染：   <img src="相对路径" data-local-path="绝对路径">
  2. 绿色模板：     <img src="相对/绝对路径">
  3. Obsidian 截图：<img src="截屏xxx.png">（裸文件名）
                    —— 本地找不到时，去 vault 按文件名递归搜（--search-dir 或 $OBSIDIAN_VAULT）
本地图缩放/压缩后转 base64 内嵌进 src，公众号粘贴富文本时会自动上传素材库。
已是 data: / http(s) 的图跳过。

用法:
    inline-images.py <html> [--output OUT] [--search-dir DIR]... \\
                     [--max-width N] [--jpeg] [--quality Q] [--no-resize]

参数:
    --output OUT     内嵌结果写到 OUT（不改原文件）；不指定则原地改写
    --search-dir DIR 找不到的图，去 DIR 递归按文件名搜（可多次）。也读环境变量 $OBSIDIAN_VAULT
    --max-width N    缩放最长边 N px（默认 1080，0=不缩放）
    --jpeg           转 JPEG（体积小 ~5x，手绘白底图可能轻微伪影）
    --quality Q      JPEG 质量 0-100（默认 82，仅 --jpeg 生效）
    --no-resize      不缩放，原图内嵌

相对路径 src 相对 <html> 目录解析。输出 stdout JSON 统计。依赖 sips（macOS 自带）。
"""
import sys
import re
import os
import json
import base64
import subprocess
import tempfile

MIME = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "webp": "image/webp", "gif": "image/gif",
}
IMG_EXT = tuple("." + e for e in MIME)


def unescape_attr(s):
    return (s.replace("&amp;", "&").replace("&quot;", '"')
             .replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">"))


def build_index(search_dirs):
    """递归索引 search_dirs 下所有图片：basename -> 绝对路径（先到先得）。"""
    idx = {}
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if not x.startswith(".")]  # 跳过 .obsidian/.git 等
            for fn in files:
                if fn.lower().endswith(IMG_EXT):
                    idx.setdefault(fn, os.path.join(root, fn))
    return idx


def encode_image(path, max_width, use_jpeg, quality):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    src, tmp = path, None
    if max_width > 0 or use_jpeg:
        out_ext = "jpg" if use_jpeg else (ext if ext in MIME else "png")
        fd, tmp = tempfile.mkstemp(suffix="." + out_ext)
        os.close(fd)
        cmd = ["sips"]
        if max_width > 0:
            cmd += ["-Z", str(max_width)]
        if use_jpeg:
            cmd += ["-s", "format", "jpeg", "-s", "formatOptions", str(quality)]
        cmd += [path, "--out", tmp]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0 and os.path.isfile(tmp) and os.path.getsize(tmp) > 0:
            src, ext = tmp, out_ext
    mime = MIME.get(ext, "image/png")
    with open(src, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    if tmp and os.path.isfile(tmp):
        os.remove(tmp)
    return b64, mime


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    html_path = args[0]
    out_path = None
    search_dirs = []
    max_width, use_jpeg, quality = 1080, False, 82
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--output":
            out_path = args[i + 1]; i += 2
        elif a == "--search-dir":
            search_dirs.append(args[i + 1]); i += 2
        elif a == "--max-width":
            max_width = int(args[i + 1]); i += 2
        elif a == "--no-resize":
            max_width = 0; i += 1
        elif a == "--jpeg":
            use_jpeg = True; i += 1
        elif a == "--quality":
            quality = int(args[i + 1]); i += 2
        else:
            print(f"⚠️ 未识别参数: {a}", file=sys.stderr); i += 1

    env_vault = os.environ.get("OBSIDIAN_VAULT", "").strip()
    if env_vault:
        search_dirs.append(env_vault)

    if not os.path.isfile(html_path):
        sys.exit(f"❌ HTML 不存在: {html_path}")

    base_dir = os.path.dirname(os.path.abspath(html_path))
    html = open(html_path, encoding="utf-8").read()
    stats = {"inlined": 0, "from_vault": 0, "skipped": 0, "missing": []}
    index = {"built": False, "map": {}}

    def find_local(src, tag):
        # 1) baoyu data-local-path（绝对）
        lp = re.search(r'data-local-path="([^"]*)"', tag)
        if lp:
            p = unescape_attr(lp.group(1))
            if os.path.isfile(p):
                return p, False
        if src:
            s = unescape_attr(src)
            p = s if os.path.isabs(s) else os.path.join(base_dir, s)
            if os.path.isfile(p):
                return p, False
            # 2) search-dir 按 basename 找（Obsidian vault 截图）
            if search_dirs:
                if not index["built"]:
                    index["map"] = build_index(search_dirs)
                    index["built"] = True
                hit = index["map"].get(os.path.basename(s))
                if hit:
                    return hit, True
        return None, False

    def process_img(m):
        tag = m.group(0)
        src_m = re.search(r'src="([^"]*)"', tag)
        src = src_m.group(1) if src_m else ""
        if src.startswith("data:") or src.startswith(("http://", "https://", "//")):
            stats["skipped"] += 1
            return tag
        path, from_vault = find_local(src, tag)
        if not path:
            stats["missing"].append(src or "(无 src)")
            return tag
        b64, mime = encode_image(path, max_width, use_jpeg, quality)
        stats["inlined"] += 1
        if from_vault:
            stats["from_vault"] += 1
        data_uri = f"data:{mime};base64,{b64}"
        tag = re.sub(r'src="[^"]*"', lambda _: f'src="{data_uri}"', tag, count=1)
        tag = re.sub(r'\s*data-local-path="[^"]*"', "", tag)
        return tag

    html = re.sub(r"<img\b[^>]*>", process_img, html)
    dest = out_path or html_path
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html)

    stats["htmlBytes"] = os.path.getsize(dest)
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
