#!/bin/bash
# publish-to-wechat.sh — 把绿色模板 HTML 里的本地图 base64 内嵌后拷到剪贴板
#
# 绿色路线下，"md → 绿色 HTML" 由 Claude（obsidian-publish skill 读 templates/wechat-green.html
# 套样式）完成；这个脚本是发布前最后一步：把绿色 HTML 里的本地图内嵌成 base64 + 拷贝。
#
# 用法：
#   bash publish-to-wechat.sh <绿色.html> [--jpeg] [--max-width N]
#
# 参数：
#   绿色.html        已套好绿色样式的 HTML（图片可以是相对路径 / 绝对路径）
#   --jpeg           图片转 JPEG 内嵌（体积小 ~5x，手绘图可能有轻微伪影；默认 PNG 无损）
#   --max-width N    图片缩放到最长边 N px（默认 1080）
#   --no-resize      不缩放，原图内嵌
#
# 依赖：python3、sips（macOS 自带）
#
# 完成后：
#   - 生成 <name>-publish.html（图片已 base64 内嵌，可双击预览；原 HTML 不动）
#   - 该内嵌版已在剪贴板，Cmd+V 粘贴到公众号编辑器，图片会自动上传素材库

set -euo pipefail

GREEN_HTML="${1:?用法: $0 <绿色.html> [--jpeg] [--max-width N]}"
shift

case "$GREEN_HTML" in
    *.md)
        echo "❌ 绿色路线下我吃的是已套好样式的 HTML，不是 md。" >&2
        echo "   先用 /obsidian-publish 把文章套成绿色 HTML（参考 templates/wechat-green.html），再传给我。" >&2
        exit 1;;
esac

if [ ! -f "$GREEN_HTML" ]; then
    echo "❌ 文件不存在: $GREEN_HTML" >&2
    exit 1
fi

# 转绝对路径；脚本目录也先存好
GREEN_HTML="$(cd "$(dirname "$GREEN_HTML")" && pwd)/$(basename "$GREEN_HTML")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Obsidian 截图自动归集：inline 找不到的本地图，会去 vault 按文件名递归抓。
# 默认指向你的 vault，可用环境变量 OBSIDIAN_VAULT 覆盖。（用 env 传，避开中文空格路径的 quoting）
export OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-}"

INLINE_OPTS=""
while [ $# -gt 0 ]; do
    case "$1" in
        --jpeg)      INLINE_OPTS="$INLINE_OPTS --jpeg"; shift;;
        --max-width) INLINE_OPTS="$INLINE_OPTS --max-width $2"; shift 2;;
        --quality)   INLINE_OPTS="$INLINE_OPTS --quality $2"; shift 2;;
        --no-resize) INLINE_OPTS="$INLINE_OPTS --no-resize"; shift;;
        *)           echo "⚠️ 未识别参数: $1" >&2; shift;;
    esac
done

OUT="${GREEN_HTML%.html}-publish.html"

echo "🖼️  内嵌图片（base64）..."
STATS=$(python3 "$SCRIPT_DIR/inline-images.py" "$GREEN_HTML" --output "$OUT" $INLINE_OPTS)
INLINED=$(echo "$STATS" | python3 -c "import json,sys; print(json.load(sys.stdin).get('inlined',0))" 2>/dev/null || echo "?")
FROM_VAULT=$(echo "$STATS" | python3 -c "import json,sys; print(json.load(sys.stdin).get('from_vault',0))" 2>/dev/null || echo "0")
HTML_KB=$(echo "$STATS" | python3 -c "import json,sys; print(round(json.load(sys.stdin).get('htmlBytes',0)/1024))" 2>/dev/null || echo "?")
MISSING=$(echo "$STATS" | python3 -c "import json,sys; print(chr(10).join(json.load(sys.stdin).get('missing',[])))" 2>/dev/null || echo "")

cat "$OUT" | pbcopy

echo "✅ 内嵌版: $OUT"
echo "✅ 内嵌图片 $INLINED 张（其中 $FROM_VAULT 张从 vault 自动抓）| 剪贴板已就绪（${HTML_KB} KB）"
if [ -n "$MISSING" ]; then
    echo "⚠️ 下列图片找不到，未内嵌（检查 src 路径是否相对 html 文件）："
    echo "$MISSING" | sed 's/^/   - /'
fi
echo ""
echo "👉 公众号编辑器 → 新建图文 → 正文区 Cmd+V（图片会自动上传素材库）"
