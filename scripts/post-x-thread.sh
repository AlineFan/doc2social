#!/bin/bash
# post-x-thread.sh — 把多段文本串成 X (Twitter) 线程发布
#
# 用法：
#   bash post-x-thread.sh thread.txt
#
# 输入文件格式（thread.txt）：
#   - 每条推文之间用 `----` 单独一行分隔
#   - 推文内部可以多行
#   - `----` 之前的内容会被合并成一条 tweet
#   - 文件开头的 `----` 会被忽略
#
# 示例 thread.txt：
#   第 1 条推文的内容
#   可以多行
#   ----
#   第 2 条推文
#   ----
#   第 3 条推文
#
# 输出：
#   - 每条推文发布后打印 URL
#   - 最后打印首条 URL（即线程入口）
#
# 依赖：
#   - opencli v1.8.0+（已装在 /usr/local/bin/opencli）
#   - 本机 Chrome 已登录 X / Twitter
#
# 安全：
#   - 失败时不重试（避免重复发推）
#   - 中途失败会断在某一条，已发的不会撤回，需手动接

set -euo pipefail

THREAD_FILE="${1:?用法: $0 thread.txt （每条推文用 ---- 分隔）}"

if [ ! -f "$THREAD_FILE" ]; then
    echo "❌ 文件不存在: $THREAD_FILE" >&2
    exit 1
fi

# 用 awk 解析：按 ---- 单独一行分段
mapfile -t POSTS < <(awk '
  BEGIN { content = "" }
  /^----+$/ {
    if (content) {
      print content
      content = ""
    }
    next
  }
  {
    if (content) content = content "\n" $0
    else content = $0
  }
  END {
    if (content) print content
  }
' "$THREAD_FILE")

if [ ${#POSTS[@]} -eq 0 ]; then
    echo "❌ 没解析到任何推文。检查文件是否用 ---- 单独一行分隔" >&2
    exit 1
fi

echo "📨 准备发 ${#POSTS[@]} 条推文..."

# 字符权重快速估算（中文 ×2 + 英文 ×1，URL 视为 23）
# 不精确，仅做预警，不阻止
for i in $(seq 0 $((${#POSTS[@]} - 1))); do
    text="${POSTS[$i]}"
    # 简单估算：中文字符（2 字节 UTF-8 一字）+ 英文（1 字节一字）
    cn_count=$(echo -n "$text" | LC_ALL=C grep -oE '[\xe4-\xe9][\x80-\xbf][\x80-\xbf]' | wc -l | tr -d ' ')
    en_count=$(echo -n "$text" | LC_ALL=C tr -d '\xe0-\xef\x80-\xbf' | wc -c | tr -d ' ')
    estimated=$((cn_count * 2 + en_count))
    if [ "$estimated" -gt 280 ]; then
        echo "  ⚠️ Post $((i+1)) 估算 $estimated 加权字符，可能超 280。继续？(y/n)"
        read -r confirm
        if [ "$confirm" != "y" ]; then exit 1; fi
    fi
done

# 发第 1 条
echo ""
echo "1/${#POSTS[@]} 发第 1 条..."
FIRST_OUT=$(opencli twitter post "${POSTS[0]}" -f yaml < /dev/null 2>&1)
FIRST_URL=$(echo "$FIRST_OUT" | awk '/^url:/ {print $2}')

if [ -z "$FIRST_URL" ]; then
    echo "❌ 第 1 条发送失败" >&2
    echo "$FIRST_OUT" >&2
    exit 1
fi
echo "✅ $FIRST_URL"

# 串 reply
PREV_URL="$FIRST_URL"
for i in $(seq 1 $((${#POSTS[@]} - 1))); do
    echo ""
    echo "$((i+1))/${#POSTS[@]} reply 上一条..."
    REPLY_OUT=$(opencli twitter reply "$PREV_URL" "${POSTS[$i]}" -f yaml < /dev/null 2>&1)
    REPLY_URL=$(echo "$REPLY_OUT" | awk '/^url:/ {print $2}')

    if [ -z "$REPLY_URL" ]; then
        echo "⚠️ 第 $((i+1)) 条发送失败，线程已断在第 $i 条" >&2
        echo "已发布的首条: $FIRST_URL" >&2
        echo "失败原因:" >&2
        echo "$REPLY_OUT" >&2
        echo ""
        echo "👉 手动操作：访问 $PREV_URL 在浏览器里手动 reply 剩下的内容" >&2
        exit 1
    fi
    echo "✅ $REPLY_URL"
    PREV_URL="$REPLY_URL"
done

echo ""
echo "🎉 线程完成 ($((${#POSTS[@]})) 条推文已串成 thread)"
echo "首条 URL（线程入口）: $FIRST_URL"
