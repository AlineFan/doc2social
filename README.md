# doc-to-social-render

把 **Markdown / Obsidian 笔记**一键渲染成**微信公众号**和**小红书**可直接发布的图文物料。包含两套渲染工具 + 对应的 Claude Code skill。

## 1️⃣ 公众号排版 · gzh-layout-cloner

克隆任意公众号文章的排版风格，套到你的 Markdown，输出可直接粘贴公众号的 inline-style HTML。

**网页版（浏览器打开即用，Chrome/Edge 最佳）** — [`web/index.html`](web/index.html)
- 拖入笔记所在文件夹（或连接 vault）→ 笔记里的 `![[图片]]` / `![](图片)` **自动 base64 内嵌**
- 选主题一键渲染 → **复制到公众号**（粘贴时图片自动上传素材库）
- 内置主题：**绿色科技风** / **极简黑白（水墨）** / **椰树风** / **极简(支持代码)**
- `#` 一级标题自动成分节头卡、`##` 二级标题成序号胶囊（绿色科技风）

**脚本版**
- [`scripts/inline-images.py`](scripts/inline-images.py) — 把 HTML 里本地图转 base64 内嵌（找不到的图可从 vault 按文件名递归找）
- [`scripts/publish-to-wechat.sh`](scripts/publish-to-wechat.sh) — 内嵌 + 复制到剪贴板

**样式模板** — [`templates/`](templates/)：每个 `<名>.json` 是一套排版主题，`<名>-preview.html` 是可视化预览。

**Claude Code skill** — [`skills/gzh-layout-cloner/`](skills/gzh-layout-cloner/)：给一篇公众号 URL → 自动提取排版组件 → 套用你的内容。

## 2️⃣ 小红书长截图 · note-to-xhs

把一篇笔记渲染成 **X（Twitter）长文视觉样式**的多张 3:4 长截图，配标题、正文、话题标签。

- [`scripts/note-to-xshots.sh`](scripts/note-to-xshots.sh) + [`scripts/render-xshots.ts`](scripts/render-xshots.ts) + [`templates/x-longform.html`](templates/x-longform.html)
- **Claude Code skill** — [`skills/note-to-xhs/`](skills/note-to-xhs/)

## 配置

图片自动内嵌需指向你的笔记库（可选）：

```bash
export OBSIDIAN_VAULT="/path/to/your/vault"
```

依赖：`python3`、`sips`（macOS 自带）；小红书长截图需 `bun` + `playwright-core` + `marked`。

## 说明

- `templates/` 里部分排版是从公众号文章提取的 **CSS 样式**（非原文内容）。
- 网页端主题名与内部模板名可能不同（「椰树风」← 模板 `瑞幸整活风`、「极简(支持代码)」← 模板 `harness教程风`）。

---
🤖 部分工具由 [Claude Code](https://claude.com/claude-code) 协助构建。
