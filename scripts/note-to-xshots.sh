#!/bin/bash
# note-to-xshots.sh — Obsidian 笔记 → X 长文视觉风格 → 多张 3:4 小红书长截图
#
# 这是 REQUIREMENTS.md 里「小红书图片」槽位的 v1 实现（之前砍掉、现重做）。
# 把一篇 .md 渲染成 @林锵锵 的 X 长文样式，按块切成多张 3:4 PNG，可直接发小红书。
#
# 用法：
#   bash note-to-xshots.sh <note.md> [--banner <置顶图 URL|路径>] [--out <目录>] [--keep-html]
#
# 参数：
#   note.md          Obsidian 笔记（首个 # 标题作大标题，正文转 X 长文样式）
#   --banner X        横幅置顶图：URL / 绝对路径 / vault 内文件名（按 basename 找）
#   --out 目录        输出目录（默认 <note 同目录>/xshots/）
#   --keep-html       保留中间产物 _preview.html（调试用）
#
# 图片解析：正文里的 ![[img.png]] 和 ![](path) 会按 basename 去 vault 递归找，
#           解析成 file:// 绝对路径，截图时由 chromium 直接加载（不丢 vault 图）。
#
# 依赖：bun、playwright-core、marked（proj04 根目录已 bun add），ms-playwright chromium（或系统 Chrome）
#
# 输出：<out>/01.png 02.png ... （1196×1595，≈3:4）

set -euo pipefail

NOTE="${1:?用法: $0 <note.md> [--banner X] [--out 目录] [--keep-html]}"
shift

case "$NOTE" in
    *.md) ;;
    *) echo "❌ 我吃的是 .md 笔记，不是 $NOTE" >&2; exit 1;;
esac
if [ ! -f "$NOTE" ]; then
    echo "❌ 笔记不存在: $NOTE" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJ_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# vault 默认指向用户的 Obsidian vault，可用环境变量覆盖（避开中文空格路径的 quoting）
export OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-/Users/doushun/本地文稿/Obsidian Vault}"

# 透传剩余参数给 bun 脚本（--banner / --out / --keep-html / --width / --dpr）
cd "$PROJ_DIR"
bun scripts/render-xshots.ts "$NOTE" "$@"
