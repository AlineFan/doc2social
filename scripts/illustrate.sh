#!/bin/bash
# illustrate.sh — 明确指令触发：codex perbrand 给【定稿】文章生成配图 + shot list
#
# ⚠️ 生图会花钱（gpt-image-2 每张有成本），且耗时几分钟。
#    只在你明确跑这个脚本时触发，绝不自动。请在文章【定稿后】再跑。
#
# 用法：
#   bash illustrate.sh <定稿.md> [--count N] [--dry-run]
#
# 参数：
#   定稿.md      已定稿的文章（按它的内容生图）
#   --count N    指定张数（默认让 perbrand 自己定 4-8 张）
#   --dry-run    只打印将执行的 codex 命令，不真跑（不花钱，验证脚本逻辑用）
#
# 产出（都在文章同目录）：
#   <article>-illustrations/   配图 PNG（16:9 横版，绿衣 IP 主角）
#   <article>-shotlist.md      shot list（文件名 / 位置锚点 / 画面 / 概念）
#   <article>-illustrate.log   codex 完整输出（隔离，不进 Claude 上下文）
#
# 下一步：让 Claude 按 shot list 的【精确原句锚点】把图插入文章，再 publish-to-wechat.sh 发布
#
# 依赖：codex CLI（已 symlink 到 /usr/local/bin/codex）、~/.codex/skills/perbrand/

set -euo pipefail

ARTICLE="${1:?用法: $0 <定稿.md> [--count N] [--dry-run]}"
shift

if [ ! -f "$ARTICLE" ]; then
    echo "❌ 文件不存在: $ARTICLE" >&2
    exit 1
fi
case "$ARTICLE" in
    *.md) ;;
    *) echo "❌ 需要 markdown 定稿文件（.md）" >&2; exit 1;;
esac

ARTICLE="$(cd "$(dirname "$ARTICLE")" && pwd)/$(basename "$ARTICLE")"
ARTICLE_DIR="$(dirname "$ARTICLE")"
NAME="$(basename "$ARTICLE" .md)"

COUNT_DESC="4-8 张"
DRY=0
while [ $# -gt 0 ]; do
    case "$1" in
        --count)   COUNT_DESC="$2 张"; shift 2;;
        --dry-run) DRY=1; shift;;
        *)         echo "⚠️ 未识别参数: $1" >&2; shift;;
    esac
done

OUTDIR="$ARTICLE_DIR/${NAME}-illustrations"
SHOTLIST="$ARTICLE_DIR/${NAME}-shotlist.md"
LOG="$ARTICLE_DIR/${NAME}-illustrate.log"

if ! command -v codex >/dev/null 2>&1; then
    echo "❌ codex 未安装/未 symlink。先跑:" >&2
    echo "   ln -s /Applications/Codex.app/Contents/Resources/codex /usr/local/bin/codex" >&2
    exit 1
fi

PROMPT="读取文章文件 ${ARTICLE}。用 perbrand 默认固定主角（苹果绿 hoodie、深色丸子头）为这篇文章生成 ${COUNT_DESC}横版 16:9 彩色手绘正文配图，逐张保存到 ${OUTDIR}/，按正文顺序命名 ${NAME}-perbrand-01.png、${NAME}-perbrand-02.png…（**必须带 \"${NAME}-\" 前缀**，避免 vault 内多篇文章配图同名冲突）
然后写一份 shot list 到 ${SHOTLIST}，每张图列出：
- 文件名（和实际保存的一致）
- 位置（引用文章里的一句【精确原句】作为插入锚点，一字不差，方便程序定位）
- 画面（生图描述）
- 核心概念（一句话）
顺序和正文逻辑一致。"

echo "🎨 perbrand 配图：$NAME"
echo "   文章: $ARTICLE"
echo "   输出: $OUTDIR/"
echo "   张数: $COUNT_DESC"

if [ "$DRY" = "1" ]; then
    echo ""
    echo "── DRY-RUN：将执行的命令（不真跑、不花钱）──"
    echo "codex exec -C \"$ARTICLE_DIR\" --dangerously-bypass-approvals-and-sandbox \"<prompt>\" < /dev/null"
    echo ""
    echo "── prompt ──"
    echo "$PROMPT"
    exit 0
fi

mkdir -p "$OUTDIR"
echo ""
echo "⏳ codex 生图中（输出→ ${LOG}，可能几分钟，不要中断）..."
if ! codex exec -C "$ARTICLE_DIR" --dangerously-bypass-approvals-and-sandbox "$PROMPT" < /dev/null > "$LOG" 2>&1; then
    echo "❌ codex 执行失败，看日志: $LOG" >&2
    exit 1
fi

GEN=$(ls "$OUTDIR"/*.png 2>/dev/null | wc -l | tr -d ' ')
echo ""
echo "✅ 生成 $GEN 张配图 → $OUTDIR/"
if [ -f "$SHOTLIST" ]; then
    echo "✅ shot list → $SHOTLIST"
else
    echo "⚠️ 没找到 shot list（perbrand 可能没写到指定路径），看日志: $LOG"
fi
echo ""
echo "👉 下一步：让 Claude 按 $SHOTLIST 的位置锚点把图插入文章定稿，再跑 publish-to-wechat.sh 发布"
