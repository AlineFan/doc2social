#!/bin/bash
# publish-to-wechat.sh — 把 markdown 渲染成公众号兼容 HTML，拷到剪贴板
#
# 用法：
#   bash publish-to-wechat.sh <article.md> [--theme <主题>]
#
# 参数：
#   article.md      markdown 文章路径（必须）
#   --theme <name>  公众号主题：default | grace | simple | modern（默认 grace）
#
# 依赖：
#   - bun（runtime）
#   - ~/.claude/skills/baoyu-skills/（已 clone）
#
# 完成后：
#   - HTML 文件保存在 article.md 同目录（article.html）
#   - HTML 已在剪贴板，直接 Cmd+V 粘贴到公众号编辑器

set -euo pipefail

ARTICLE_MD="${1:?用法: $0 article.md [--theme name]}"
shift

if [ ! -f "$ARTICLE_MD" ]; then
    echo "❌ 文件不存在: $ARTICLE_MD" >&2
    exit 1
fi

THEME="grace"

while [ $# -gt 0 ]; do
    case "$1" in
        --theme) THEME="$2"; shift 2;;
        *)       echo "⚠️ 未识别参数: $1" >&2; shift;;
    esac
done

BAOYU_DIR="$HOME/.claude/skills/baoyu-skills"

if [ ! -d "$BAOYU_DIR" ]; then
    echo "❌ baoyu-skills 未安装。先跑: cd ~/.claude/skills && git clone https://github.com/JimLiu/baoyu-skills.git" >&2
    exit 1
fi

echo "📝 渲染公众号 HTML（主题: $THEME）..."
cd "$BAOYU_DIR"
RAW_RESULT=$(bun skills/baoyu-markdown-to-html/scripts/main.ts "$ARTICLE_MD" --theme "$THEME" --cite 2>&1)

JSON_LINE=$(echo "$RAW_RESULT" | tail -1)
HTML_PATH=$(echo "$JSON_LINE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('htmlPath',''))" 2>/dev/null || echo "")

if [ -z "$HTML_PATH" ] || [ ! -f "$HTML_PATH" ]; then
    echo "❌ 渲染失败" >&2
    echo "$RAW_RESULT" >&2
    exit 1
fi

cat "$HTML_PATH" | pbcopy

echo "✅ HTML: $HTML_PATH"
echo "✅ 剪贴板已就绪（$(wc -c < "$HTML_PATH" | tr -d ' ') bytes）"
echo ""
echo "👉 打开公众号编辑器 → 新建图文 → 正文区 Cmd+V"
