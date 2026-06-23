---
name: note-to-xhs
description: 把一篇 Obsidian/markdown 笔记做成「可直接发小红书」的整套物料——按 @林锵锵 的 X（Twitter）长文视觉样式渲染成多张 3:4 长截图，再配上小红书标题、正文文案、话题标签。当用户说「把这篇笔记/md 发小红书」「这篇做成小红书图文」「note-to-xhs」「按 X 样式做小红书长截图」「给这篇配标题和文案发小红书」时使用。输入是 1 个 .md 文件路径（可选一张置顶 banner 图）。
---

# note-to-xhs：笔记 → 小红书图文物料

把一篇 markdown 笔记，一条龙做成小红书可发的物料：**X 长文样式长截图 + 标题 + 正文文案 + 话题标签**。

## 输入

- **必填**：1 个 markdown 笔记路径（通常在 Obsidian vault）
- **可选**：`--banner <图路径/URL/vault内文件名>` 置顶横幅图（不给则首图无横幅）

## 产出（4 件）

1. 多张 3:4 长截图 PNG（X 长文视觉样式，@林锵锵 身份）
2. 小红书标题（dbs 公式匹配，多候选 + Top 3）
3. 小红书正文文案（按固定内容风格，≤100 字）
4. 话题标签

---

## 流程（4 步，按顺序执行）

### Step 1 · 渲染长截图

跑渲染脚本（proj04 内）：

```bash
bash /Users/doushun/Desktop/workspace/proj04-obsidian-publisher/scripts/note-to-xshots.sh "<note.md>" [--banner "<图>"] --out /tmp/xhs-<slug>
```

- 输出 N 张 `01.png 02.png …`（1196×1594，3:4）到 `--out` 目录
- 脚本自带：标题取笔记顶部 H1 或文件名、正文 X 长文样式、`![[图]]` 按 basename 去 vault 找、智能连续切（文字不切半行 / 图可跨页 / 留白极小）、互动数字随机、@林锵锵 头像
- 跑完把 stdout 的 JSON（tiles / missing）读出来；**若 `missing` 非空，提示用户哪几张图没找到**
- 完事 `open <out目录>` 让用户看

### Step 2 · 生成标题（先用 dbs-xhs-title）

调用 `/dbs-xhs-title` skill，把笔记核心内容 + 已定稿的正文文案一起传给它（标题要和文案咬合）：

- 让它按 75 个爆款公式匹配，输出 5–8 个候选（标注公式编号）+ Top 3
- 标题硬规范：≤20 字（含标点）、留悬念不剧透、用普世词扩大流量池
- Top 1 通常用作首图大字封面

### Step 3 · 生成正文文案（用固定内容风格）

**先读 `references/caption-style.md`**，严格照那套风格写正文：

- ≤100 字、开头直接抛反差观点、对仗金句收尾、0 emoji、不强行加互动钩子
- 写完过一遍 caption-style.md 末尾的自检清单
- 如果用户已经给了定稿文案，**直接用用户的，不要自作主张改写**

### Step 4 · 配话题标签

- **核心固定标签**（AI/成长赛道）：`#AI #人工智能 #ai工具 #认知升级 #独立思考 #深度思考 #个人成长 #普通人如何用ai #aigc #自我提升`
- 按这篇的具体主题增删 2–3 个更精准的（如讲 Claude Code 就加 `#claude #AI编程`）
- 总数控制在 8–12 个

---

## 最终输出格式

给用户一张「发布物料卡」，四样齐全、可直接复制：

```
📂 图片：<out 目录>（N 张 3:4，已 open）

【标题】Top 1（+附 2 个备选）
<标题>

【正文】
<≤100 字文案>

【标签】
<8–12 个 # 标签>
```

末尾提示：标题想换 Top 2/3、文案想调长短，直接说。

---

## 边界

- ❌ 不自动发布到小红书（v1 手动发；未来可接 `opencli xiaohongshu publish`）
- ❌ 不改写正文长文内容（那是 obsidian-publish 的活；本 skill 只做「成品笔记 → 小红书物料」）
- ❌ 一次只处理一篇 md
- 文案风格以 `references/caption-style.md` 为准；标题方法以 dbs-xhs-title 为准
