# 个人内容创作工作流 — 需求文档

**版本**: v1.0
**日期**: 2026-06-21
**项目目录**: `/Users/doushun/Desktop/workspace/proj04-obsidian-publisher/`
**状态**: 已确认（用户确认 2026-06-21）
**目标读者**: 开发者（可以是用户本人或新接手的人，第一次看这份文档要能直接动手开干）

---

## 0. TL;DR

一个 **macOS 终端原生的个人内容创作流水线**，从 Obsidian vault 取材，在 Claude Code 里跑 skill 链做研究/整合，输出 **公众号长文 + 小红书图文 + X 内容 + 短视频口播大纲 + 横版配图** 5 类内容，通过 opencli 推到各平台。

**不是网站**，不是 Web 工具，不是浏览器扩展。整个工作流住在终端里。

第一版预计 **1 个完整工作日** 落地。

---

## 1. 项目本质

**终端原生命令工作流**（CLI-first），不是网站。

在 Claude Code 里通过命令触发 skill（`~/.claude/skills/`）+ opencli 命令 + Codex CLI 命令，完成从素材到多平台发布的全流程。

**为什么不是 Web 工具**：
- 用户原本想做 Web 工具（task #6 历史决议），但调研后发现 Claude Code + Obsidian vault + opencli + Codex 已经能覆盖所有需求
- Obsidian 自身就是文件浏览器 — 再做一个 Web 文件浏览器是重复
- 浏览器扩展存在沙箱限制（读不到本地文件、调不了本地命令）
- 终端原生 = 零安装、零部署、最快上线

---

## 2. 目标使用人

- **使用人**：用户本人（单用户，doushun）
- **多用户支持**：不需要
- **登录/付费/审核**：不需要
- **平台**：macOS（Apple Silicon 或 Intel 均可）
- **已具备环境**（不需要再装的）：
  - Claude Code 订阅（Pro / Max）
  - opencli v1.8.0 安装于 `/usr/local/bin/opencli`
  - Codex Desktop App 安装在 `/Applications/Codex.app/`，含 `~/.codex/skills/perbrand/` skill
  - Obsidian vault 在 `/Users/doushun/本地文稿/Obsidian Vault/`
  - macOS 自带 zsh + Homebrew

---

## 3. 核心能力（5 类输出）

每次跑完整一次工作流，按需要可产出以下 5 类内容的任意组合：

| # | 输出类型 | 第一版形态 | 工具栈 |
|---|---------|---------|------|
| 1 | **微信公众号长文** | markdown → 应用学到的样式 → 富 HTML（人工粘贴一次） | doocs/md (本地服务) + 自写 `wechat-style-extract` skill |
| 2 | **小红书图文** | 封面 + 5-7 张内容卡 PNG | [baoyu-skills](https://github.com/JimLiu/baoyu-skills) (22.1k stars, MIT, 2026-06-20 还在发版) |
| 3 | **X 内容** | 单条 tweet (≤280 字符) + Thread 线程 (8-10 条) | 现有 `~/.claude/skills/obsidian-publish/` skill |
| 4 | **短视频口播大纲** | 结构化大纲（抖音/视频号/TikTok 规格） | 新写 `short-video-outline` skill |
| 5 | **配图（横版）** | perbrand 默认主角 4-8 张 16:9 PNG | Codex CLI + `~/.codex/skills/perbrand/` |

---

## 4. 双路径输入

工作流支持两种触发方式：

### 路径 A — 多素材模式（默认）

- **输入**：从 Obsidian vault 选 N 篇笔记（已有的 markdown 文件）
- **处理**：整合 N 篇笔记的逻辑关联 → 按用户判断写成一篇长文
- **触发**：在 Claude Code 里 `/obsidian-publish` + 多个文件路径

### 路径 B — 研究模式

- **输入**：用户输入 1 个主题（如 "loop 工程"）
- **处理**：
  1. STORM 6 视角研究（Practitioner / Academic / Skeptic / Economist / Historian / Safety Researcher）
  2. 用 opencli 抓 X / Reddit / Hackernews 真实社区声音（**信源准入门槛**：作者 followers ≥ 3k + 推文 views ≥ 5k）
  3. 整合为 briefing
  4. briefing 作为素材进路径 A 的整合流程
- **触发**：在 Claude Code 里 `/obsidian-publish 试试这个主题 X`

两条路径都通过现有的 `~/.claude/skills/obsidian-publish/` skill 编排。

---

## 5. 完整使用流程

```
[Obsidian vault]
    ↓ 选文件 (路径 A) 或 输入主题 (路径 B)
[Claude Code 触发 obsidian-publish skill]
    ↓ 整合 / 研究
[长文 markdown 定稿]
    ↓
    ├──→ baoyu-skills          → 小红书 5-7 张 PNG
    ├──→ codex perbrand        → 配图 4-8 张 16:9 PNG (横版)
    ├──→ doocs/md + 学到的样式  → 公众号富 HTML
    │                              ↓ 人工 Cmd+C 粘贴一次
    │                          opencli weixin create-draft
    │                              (填标题/作者/摘要/封面/存草稿)
    │                              ↓
    │                          公众号草稿箱 (人工点"发布")
    ├──→ short-video-outline   → 抖音/视频号/TikTok 大纲
    └──→ X 内容                 → opencli twitter post
```

---

## 6. 公众号自动化边界（重要 — 不是全自动）

### ✅ 自动的部分

通过 `opencli weixin create-draft`：
- 填标题（`--title`）
- 填作者（`--author`）
- 填摘要（`--summary`）
- 上传封面图（`--cover-image <本地路径>`，opencli 会先上传到正文再设为封面）
- 创建草稿（保存到公众号草稿箱）

通过 doocs/md：
- 应用学到的 CSS 样式
- 渲染 markdown 为公众号兼容的富 HTML

### 🤚 半自动的部分

- **正文 HTML 必须人工 Cmd+C 复制 → 粘贴到公众号编辑器一次**
- 公众号编辑器会保留 doocs/md 的内联样式（标题字号、引用块、代码块都正常）

### ⚠️ 关键技术真相（来自源码 review）

`opencli weixin create-draft` 的 `<content>` 参数**只接受纯文本**：
- 源码（`/usr/local/lib/node_modules/@jackwener/opencli/clis/weixin/create-draft.js` 第 42-54 行）用 `document.execCommand('insertText', false, content)` 把字符串原样塞进 contenteditable
- markdown 的 `#` `**` 会原样显示，HTML 的 `<h1>` 会以 7 个字面字符出现
- 没有 markdown 解析、没有 HTML 解析、没有富文本粘贴路径

**所以**：正文排版必须靠 doocs/md 渲染 + 人工粘贴。opencli 只能填元数据。

### 🔐 前提

- 在本机 Chrome 手动登录 `mp.weixin.qq.com` 一次
- opencli 通过 Browser Bridge 复用 Chrome 的 cookie session
- 没有 CLI 登录子命令，必须人工登录

---

## 7. 公众号样式抽取流程（新写的 skill）

新建 skill：`~/.claude/skills/wechat-style-extract/`

### 输入

1-3 篇你喜欢的样板公众号文章 URL（如 `https://mp.weixin.qq.com/s/xxxxx`）

### 处理

1. **fetch HTML**：用 fetch + cheerio 抓样板文章 HTML
2. **抽 inline style**：用 cheerio 遍历所有 inline `style=""` 属性，统计常用的字号 / 颜色 / 间距 / 边框
3. **结构化 JSON spec**：让 Claude 把抽到的样式整理成 JSON：
   ```json
   {
     "primary_color": "#9a6a3a",
     "font_family": "\"Songti SC\", \"STSong\", Georgia",
     "h1": { "font_size": "24px", "font_weight": "600", ... },
     "h2": { ... },
     "blockquote": { ... },
     "code": { ... },
     "p_margin": "12px 0"
   }
   ```
4. **生成 CSS**：第二次 Claude 调用，把 JSON spec 转成 doocs/md 格式的 CSS theme：
   ```css
   h1 { border-bottom: 2px solid var(--md-primary-color); ... }
   h2 { background: var(--md-primary-color); color:#fff; ... }
   blockquote { border-left: 4px solid var(--md-primary-color); ... }
   .codespan { ... }
   ```

### 输出

保存到 `~/.claude/skills/wechat-style-extract/themes/<theme-name>.css`

### 应用

每次跑 `wechat-format <md>` 时：
- 读 markdown 文件
- 注入选定的 theme CSS（通过 doocs/md 的 cssEditor store）
- 输出富 HTML

### 工程量

~150 行 Node（cheerio + @anthropic-ai/sdk + 文件 IO），半天落地。

### 参考

- [doocs/md GitHub](https://github.com/doocs/md) (12.8k stars)
- 默认 theme 模板：`https://raw.githubusercontent.com/doocs/md/main/packages/shared/src/assets/default-custom-theme.txt`
- themeExporter 源码：`https://raw.githubusercontent.com/doocs/md/main/packages/core/src/theme/themeExporter.ts`

---

## 8. 配图（横版 + 竖版）

### 横版（第一版做） — perbrand 已就绪

资产位置：
```
~/.codex/skills/perbrand/
├── SKILL.md (4964 字节, name: perbrand)
├── assets/default-character-green-hoodie.png  ← 默认主角已锁定
├── references/article-workflow.md
└── references/prompt-template.md
```

调用方式（新写 `~/.claude/skills/article-illustrate/` wrapper skill）：

```bash
cat /path/to/article.md | codex exec \
  -C /path/to/article-dir \
  --dangerously-bypass-approvals-and-sandbox \
  "用 perbrand 默认固定主角给这篇文章生成 4-8 张 16:9 彩色手绘正文配图，保存到 assets/article-illustrations/" \
  < /dev/null
```

⚠️ **关键坑**：`< /dev/null` 必须有 — Codex CLI 在非 TTY 下会等 stdin EOF 然后 hang。Claude Code 的 Bash 是非 TTY 环境。

### 一次性配置（PATH 修复）

```bash
ln -s /Applications/Codex.app/Contents/Resources/codex /usr/local/bin/codex
```

之后就能用 `codex exec "..."` 而不是绝对路径。

### 竖版（第二阶段做）

- 整篇文章浓缩到一张图（小红书 3:4 或 公众号 21:9 + 1:1 封面）
- 候选方案：[op7418/guizang-social-card-skill](https://github.com/op7418/guizang-social-card-skill) (3.8k stars)
- 注意：AGPL-3.0 协议，仅个人使用不受影响

### 模型说明

- "image2" = **gpt-image-2**（OpenAI 旗舰图像模型，2026-04-21 发布）
- 价格：$0.005（low）– $0.41（4K）/张
- Codex CLI 原生集成，走 ChatGPT 账号（不用 API key）
- 99% 字符准确率（含 CJK）

---

## 9. 短视频口播大纲（新写的 skill）

新建 skill：`~/.claude/skills/short-video-outline/`

### 第一版

**输入**：长文 markdown
**输出**：结构化大纲，适配抖音 / 视频号 / TikTok 短视频规格

大纲格式示例：
```markdown
# [视频标题]

时长：60-90 秒

## 钩子 (0-3s)
- 一句话点出最反常识的洞察

## 现象 (3-15s)
- 具体当下事件 + 数字
- 不超过 2 个画面切换

## 核心冲突 (15-45s)
- 大众认知 vs 真相
- 用 1 个具体案例支撑

## 行动 (45-75s)
- 给一个今天就能做的具体动作

## 收尾 + 引导互动 (75-90s)
- 一句金句
- "评论区告诉我"

## 配图建议
- 0-3s: [画面描述]
- 3-15s: [画面描述]
- ...
```

**不写完整脚本** — 留给用户自己手写。

### 第二阶段

- 用户积累了爆款数据后
- 结合 dbs skill（dontbesilent 系列：dbs-hook / dbs-content / dbs-xhs-title）
- 自动生成完整口播文案

### 工程量

~100 行的 SKILL.md prompt + references/ 目录里放抖音/TikTok 各 1 篇样板文案。2 小时落地。

---

## 10. 范围控制

### 第一版（MVP）— ⚠️ 2026-06-21 重估：1 工作日 → **2-3 小时**

**重估原因**：baoyu-skills 装完后发现里面 20+ skill，6 个 skill 通过 Workflow 评估后确认：4 个 baoyu skill 是我们计划的"自写 skill"的超集，直接砍掉。

| # | 任务 | 工程量 | 状态 |
|---|------|--------|------|
| 1 | Codex CLI 软链接 | 1 分钟 | ✅ 2026-06-21 完成 |
| 2 | 装 baoyu-skills 到 `~/.claude/skills/` | 10 分钟 | ✅ 2026-06-21 完成（含 20+ skill）|
| 3 | ~~Fork doocs/md~~ | ~~30 分钟~~ | ❌ **砍掉**（baoyu-markdown-to-html 80% 场景覆盖，doocs/md 收窄到「复刻样板号」时再装）|
| 4 | ~~写 wechat-style-extract~~ | ~~半天~~ | ❌ **窄化保留**：仅复刻特定样板号视觉时启用，日常用 baoyu grace 主题 |
| 5 | ~~写 wechat-draft~~ | ~~1 小时~~ | ❌ **砍掉**（baoyu-post-to-wechat 是超集：API + md→HTML + 图片上传 + 封面 fallback）|
| 6 | 写 `short-video-outline` skill（**薄版**） | 1 小时 | ⏳ 2026-06-21 dbs 调研：dbs 全系是诊断/优化导向，无法直接产出五段大纲。自写薄版，钩子段引用 dbs-hook 规则，输出后建议跑 dbs-content 自检 |
| 7 | ~~写 `article-illustrate` skill~~ | ~~1 小时~~ | ❌ **砍掉** 2026-06-21 用户决策：直接用 codex perbrand 一行命令，不包装 wrapper skill |
| 8 | 一次性手动登录 mp.weixin.qq.com | 5 分钟 | ✅ 2026-06-21 完成 |
| 🆕 9 | 装 imagegen backend（codex imagegen / baoyu-image-gen 二选一）| 10 分钟 | ⏳ 待做 — baoyu skill 依赖 |
| 🆕 10 | 建 EXTEND.md（baoyu skill 持久化偏好）| 15 分钟 | ⏳ 待做 |
| 🆕 11 | 写 `post-x-thread.sh`（opencli twitter post + reply 链式串）| 30 分钟 | ✅ 2026-06-21 完成 — `proj04-obsidian-publisher/scripts/post-x-thread.sh`。bash awk 解析 ---- 分段，逐条 post + reply。语法和解析已测，待真发 thread 验证 |
| 12 | 跑 5 条验证命令（baoyu 各 skill）| 30 分钟 | ⏳ 待做 |
| | **合计实际剩余** | **~2-3 小时** | |

### baoyu skill 决策表（详见 task #14 Workflow `wk3itq985` 调研结果）

| baoyu skill | 决策 | 用法 |
|------------|------|------|
| `baoyu-post-to-wechat` | **拆分用**（2026-06-22 实测后调整） | 浏览器自动化找不到公众号编辑器（UI 改了？）。改方案：仅复用其中的 `scripts/md-to-wechat.ts`（独立 CLI 可调，含 footnote / Mermaid / inline style），发布走 opencli weixin create-draft 占位 + 人工粘贴一次 |
| `baoyu-markdown-to-html` | **直接用 80%** | 默认 grace/modern 主题，复刻样板号场景才走 doocs/md |
| `baoyu-article-illustrator` | **不用**（2026-06-21 用户决策修正） | 配图直接走 codex perbrand。baoyu illustrator 是"信息图风格"，跟 perbrand 的"绿衣 IP 主角"路线冲突，混用没意义 |
| `baoyu-cover-image` | **不用** | 2026-06-21 用户决策：封面图 v1 不自动生成；未来用 perbrand × baoyu-cover-image 拼接方案做 |
| `baoyu-xhs-images` | **不用**（2026-06-22 用户决策） | 小红书图片 v1 先空着，未来重做（可能用 perbrand × 其他方案 mix）|
| `baoyu-post-to-x` | **不用** | 浏览器模拟点击 + 无 thread，opencli twitter API 完胜 |

### 5 条 v1 验证命令（按顺序跑通）

```bash
# 1. v1 公众号发布（baoyu md-to-wechat + opencli + 人工粘贴一次）
bash proj04-obsidian-publisher/scripts/publish-to-wechat.sh test/v1-test.md --cover /path/to/cover.jpg

# 2. baoyu-markdown-to-html 验证（grace 主题 + cite 转底部引用）
npx baoyu-md test.md --theme grace --cite -o test.html && open test.html

# 3. baoyu-cover-image quick 模式验证（公众号首图）
claude --skill baoyu-cover-image "为 test.md 生成封面 --quick --aspect 2.35:1"

# 4. ~~baoyu-xhs-images~~（2026-06-22 砍掉，小红书图片 v1 不做）

# 5. codex perbrand 验证（横版 4-8 张 16:9 绿衣 IP 配图，**不用 baoyu illustrator**）
cat test.md | codex exec -C $(pwd) --dangerously-bypass-approvals-and-sandbox \
  "用 perbrand 默认 green-hoodie 主角给这篇文章生成 4-8 张 16:9 彩色手绘正文配图，保存到 assets/article-illustrations/" \
  < /dev/null
```

**前置条件**：① imagegen backend 就绪（codex imagegen 或 baoyu-image-gen）② EXTEND.md 建好

### 第二阶段（之后）

- **视频/音频转文本**：集成 [chubbyguan/chubbyskills](https://github.com/chubbyguan/chubbyskills) (431 stars)，支持抖音/B站/小红书/公众号/X/播客
- **完整口播脚本**：结合 dbs skill 集成（dbs-hook / dbs-content / dbs-xhs-title）
- **竖版长图**：集成 op7418/guizang-social-card-skill
- **Hyperframe 动画 HTML**：从 Claude Code 调 hyperframe 生成动画 HTML

### 第三阶段（之后）

- 小红书卡片图迭代（"简版"，具体形态待定）

---

## 11. 不做的事（明确边界）

为防止 scope creep，以下明确**不在 v1 范围内**：

- ❌ **不建 Web 工具** / 不建网站 / 不写浏览器扩展
- ❌ **不做多用户、登录、付费、订阅**
- ❌ **不做对外发布平台**（不是 SaaS）
- ❌ **不在 Obsidian 里装 Claudian / Smart Composer / Copilot 等 AI 插件**（用户选 A 方案 — 终端原生）
- ❌ **不接 Claude API**（用 Claude Code 订阅即可）
- ❌ **不写完整口播脚本**（第一版只给大纲）
- ❌ **不做视频/音频转文本**（第二阶段做）
- ❌ **不做竖版长图**（第二阶段做）

---

## 12. 已确认的关键技术细节（开发时不踩坑）

### opencli weixin create-draft

- `<content>` 参数**只吃纯文本**（不解析 markdown / HTML）
- 公众号正文排版**必须**预先用 doocs/md 渲染好 → 人工粘贴
- 必须在本机 Chrome 手动登录 `mp.weixin.qq.com` 一次
- 没有 CLI 登录子命令
- `--cover-image` 只接本地路径，只设封面（不支持正文图）

### Codex CLI

- 已装于 `/Applications/Codex.app/Contents/Resources/codex` (v0.142.0-alpha.6)
- PATH 里没有 — 需要 `ln -s` 软链
- 非 TTY 下会 hang — **必须** `< /dev/null`
- 推荐 flag：
  - `-C <dir>` 设工作目录
  - `--dangerously-bypass-approvals-and-sandbox` 全自动化
  - `--ephemeral` 不持久化 session（按需）
- 走登录的 ChatGPT 账号，不用 API key
- skill 系统跟 Claude Code 一样按 description 语义匹配 — **不需要 `--skill` flag**

### Codex 图像模型（gpt-image-2，用户口中的 "image2"）

- 真实存在，2026-04-21 发布
- $0.005（low）/张到 $0.41（4K）/张
- 99% 字符准确率，含 CJK
- 触发方式：在 prompt 里写 "生成 X 图保存到 ./images/x.png"，或显式 `$imagegen`

### opencli codex adapter

- 不是 spawn CLI 子进程
- 是控制 Codex Desktop App（用 CDP 协议）
- 子命令：`ask` / `send` / `new` / `history` / `export` / `model` / 等
- **从 Claude Code 调 Codex 不走这条路** — 直接 spawn `codex exec` 更轻

### baoyu-skills 安装

```bash
cd ~/.claude/skills
git clone https://github.com/JimLiu/baoyu-skills.git
# 之后 Claude Code 自动识别 ~/.claude/skills/baoyu-skills/<each-skill>
```

调用：在 Claude Code 里 `/baoyu-xhs-images /path/to/article.md` → 输出 PNG 到默认目录

### perbrand skill 已就绪

- 位置：`~/.codex/skills/perbrand/`
- 默认主角：`assets/default-character-green-hoodie.png`
- 不在 GitHub 公网 — 用户自己装的
- 横版 4-8 张 16:9 PNG 是 perbrand 的强项
- 竖版长图 perbrand 不一定支持，看 `~/.codex/skills/perbrand/SKILL.md`

---

## 13. 工具栈完整清单

### 已安装（不用做）

| 工具 | 位置 / 版本 | 用途 |
|------|----------|------|
| Claude Code | Pro/Max 订阅 | 主编排器 |
| `~/.claude/skills/obsidian-publish/` | 已存在 | 整合 + 研究 → 3 平台 |
| Codex Desktop App | `/Applications/Codex.app/` (v0.142.0-alpha.6) | perbrand 生图 |
| `~/.codex/skills/perbrand/` | 已存在 | 配图（默认主角 green-hoodie） |
| opencli | `/usr/local/bin/opencli` v1.8.0 | 跨平台发布 / 抓数据 |
| Obsidian | macOS App | 笔记库 |

### 第一版要装的

| 工具 | 装在哪 | 用途 |
|------|----------|------|
| [baoyu-skills](https://github.com/JimLiu/baoyu-skills) | `~/.claude/skills/baoyu-skills/` | 小红书卡片 |
| [doocs/md](https://github.com/doocs/md) (12.8k stars) | 本地 fork + 跑 dev 服务 | 公众号样式渲染 |
| `wechat-style-extract` skill | `~/.claude/skills/wechat-style-extract/` | 学样式 → 生成 CSS |
| `wechat-draft` skill | `~/.claude/skills/wechat-draft/` | 包装 opencli weixin |
| `short-video-outline` skill | `~/.claude/skills/short-video-outline/` | 短视频大纲 |
| `article-illustrate` skill | `~/.claude/skills/article-illustrate/` | 包装 codex perbrand |

### 第二阶段要装的（不在 v1 范围）

- [chubbyguan/chubbyskills](https://github.com/chubbyguan/chubbyskills) (431 stars) — 视频/音频转文本
- [op7418/guizang-social-card-skill](https://github.com/op7418/guizang-social-card-skill) (3.8k stars) — 竖版长图
- Hyperframe (待定具体集成方式)

### 关键依赖

- Node.js（macOS 自带 / brew install node）
- cheerio (`npm i cheerio`)
- @anthropic-ai/sdk (`npm i @anthropic-ai/sdk`) — 仅 wechat-style-extract 用到（一次性学样式）

---

## 14. 验收标准

第一版完工的判断：

- [ ] 跑 `/obsidian-publish 试试这个主题 loop 工程` → 输出 4 平台 markdown
- [ ] 跑 `/wechat-style-extract https://mp.weixin.qq.com/s/xxx https://mp.weixin.qq.com/s/yyy https://mp.weixin.qq.com/s/zzz` → 输出 CSS theme
- [ ] 跑 `/wechat-format article.md` → 输出富 HTML 进剪贴板
- [ ] ~~跑 `/baoyu-xhs-images article.md`~~（2026-06-22 砍）
- [ ] 跑 `/article-illustrate article.md` → 输出 4-8 张横版配图
- [ ] 跑 `/short-video-outline article.md` → 输出大纲
- [ ] 跑 `/wechat-draft article.md --title "..." --cover cover.png` → 公众号草稿箱多一篇
- [ ] 手动粘贴富 HTML → 公众号草稿排版正确

---

## 15. 引用 / 参考

### 工具仓库

- [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) — 22.1k stars
- [doocs/md](https://github.com/doocs/md) — 12.8k stars
- [openai/codex](https://github.com/openai/codex)
- [jackwener/opencli](https://github.com/jackwener/opencli) — v1.8.0
- [chubbyguan/chubbyskills](https://github.com/chubbyguan/chubbyskills) — 第二阶段
- [op7418/guizang-social-card-skill](https://github.com/op7418/guizang-social-card-skill) — 第二阶段

### 模型 / API

- [OpenAI gpt-image-2 model page](https://developers.openai.com/api/docs/models/gpt-image-2)
- [OpenAI Pricing](https://openai.com/api/pricing/)
- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference)

### 项目内部文档

- `README.md` — 项目总览
- `skills/obsidian-publish/SKILL.md` — 现有 obsidian-publish skill 主文档
- `skills/obsidian-publish/references/storm-research-mode.md` — STORM 研究模式细节
- `skills/obsidian-publish/prompts/dbs-rules.md` — dontbesilent 风格规则

---

## 16. V1 定稿框架 + Skill 功能速查（2026-06-22 完工）

> **回到这份文档不知道用哪个 skill 时，直接查这一章**。每个 skill / script 一段说明：定位 / 输入 / 输出 / 触发方式 / 命令示例 / 使用场景。

### 16.0 端到端工作流图（定稿）

```
┌──────────────────────────────────────────────────────────────────┐
│  输入                                                              │
│  ┌──────────────────────┐    ┌──────────────────────┐            │
│  │ N 篇 Obsidian 笔记   │    │ 1 个研究主题（明示） │            │
│  └─────────┬────────────┘    └──────────┬───────────┘            │
│            │ 路径 A 多素材               │ 路径 B 研究模式         │
│            │                              │                        │
│            ▼                              ▼                        │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  /obsidian-publish skill                              │        │
│  │  - 多素材整合（路径 A）                                │        │
│  │  - STORM 6 视角 + opencli 抓社区声音（路径 B）         │        │
│  │  - 信源准入门槛 ≥3k followers + ≥5k views             │        │
│  │  - dbs-rules 自检 + khazix L1-L4 自检                 │        │
│  └────────────────────┬──────────────────────────────────┘        │
│                       │                                            │
│                       ▼ 定稿长文 markdown                          │
└──────────────────────┬───────────────────────────────────────────┘
                       │
   ┌───────────────────┼─────────────────────┬─────────────────────┐
   │                   │                     │                     │
   ▼                   ▼                     ▼                     ▼
┌─────────────┐ ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ 公众号长文   │ │ 横版正文配图     │ │ X 内容           │ │ 短视频大纲       │
│             │ │                 │ │                  │ │                 │
│ publish-to- │ │ codex perbrand  │ │ obsidian-publish │ │ /short-video-   │
│ wechat.sh   │ │ 一行命令         │ │ 已生成内容       │ │ outline skill   │
│             │ │                 │ │                  │ │                 │
│ + 手动粘贴一次│ │ green-hoodie    │ │ post-x-thread.sh │ │ 5 段骨架        │
│             │ │ 4-8 张 16:9 PNG │ │ 链式 reply 串    │ │ + 配图建议      │
└─────────────┘ └─────────────────┘ └──────────────────┘ └──────────────────┘

不在 v1：小红书图片（未来 mix）/ 完整口播脚本（第二阶段 dbs）/ 公众号封面自动化
```

---

### 16.1 obsidian-publish skill — **内容创作中枢**

**位置**：`~/.claude/skills/obsidian-publish/`

**一句话定位**：把多篇零散素材（路径 A）或 1 个主题（路径 B）→ 改写成公众号长文 + X 内容 + 小红书内容的多平台素材。

**输入**：
- **路径 A 多素材模式**（默认）：N 篇 Obsidian markdown 笔记的路径
- **路径 B 研究模式**（用户明示触发）：1 个研究主题词

**输出**：3 平台改写素材
- 公众号长文 markdown
- X 内容（单条 + 线程）
- 小红书图文（标题用 dbs 75 公式 + 文案 + 卡片图分段建议 + tag）

**触发方式**：
- 路径 A：`/obsidian-publish` + 文件路径，或「这些素材帮我写成公众号 X 小红书」「整合多份笔记成文章」「一稿三发」
- 路径 B：「试试这个主题 X」「用 STORM 研究 X」「研究这个话题 X」「/storm X」「我没有素材，帮我研究 X」「深入研究 X」

**关键内置能力**：
- STORM 6 视角研究（Practitioner / Academic / Skeptic / Economist / Historian / Safety Researcher）
- opencli twitter / reddit / hackernews 抓社区真实声音
- **信源准入门槛**：作者 followers ≥ 3,000 + 推文 views ≥ 5,000（两者都满足）
- 围绕 topic 搜，**不在帖子的回复区搜**
- Step 0.5.5 fact-check：所有具体引用 WebSearch 验证
- Step 0.5.6 frame switch：跑完 STORM 切换 framing，避免产出讲 STORM 而非主题
- dbs-rules.md 五维诊断 + 文字洁癖 + 表达效率
- khazix L1-L4 自检（禁用词 grep / 风格一致性 / 内容质量 / 活人感）
- 5 种文章原型（调查实验 / 产品体验 / 现象解读 / 工具分享 / 方法论分享）
- 75 个小红书标题公式（dbs-xhs-titles.md）

**使用场景**：
- 我有几篇 Obsidian 笔记想串成一篇公众号文章
- 我想研究一个新主题想发出去
- 我想要长文 + X 内容 + 小红书内容一次性产出

**不做**：
- 不写完整短视频口播脚本（用 short-video-outline 出大纲，第二阶段 dbs 出文案）
- 不生成图片（配图用 codex perbrand，小红书图片 v1 不做）
- 不自动发布（发布用各 publish-to-* 脚本）

---

### 16.2 short-video-outline skill — **短视频大纲生成**

**位置**：`~/.claude/skills/short-video-outline/SKILL.md`

**一句话定位**：1 篇定稿长文 → 抖音/视频号/TikTok 短视频的五段结构化大纲（不写完整口播文案）。

**输入**：1 篇定稿 markdown 长文（通常是 obsidian-publish 的产物）

**输出**：5 段大纲
- 段 1 · 钩子（0-3s）：画面 + 口播要点 + 配图建议
- 段 2 · 现象（3-15s）：画面 + 口播要点 + 配图建议
- 段 3 · 核心冲突（15-45s）：画面 + 口播要点 + 配图建议
- 段 4 · 行动（45-75s）：画面 + 口播要点 + 配图建议
- 段 5 · 收尾 + 引导互动（75-90s）：画面 + 口播要点 + 配图建议

**触发方式**：`/short-video-outline`、「写个短视频大纲」「这篇文章做成抖音」「TikTok 大纲」「视频号大纲」

**关键内置能力**：
- 6 类 Hook 优先级表（引用 dbs-hook 规则）
- 禁止的钩子类型清单（自问自答 / 长铺垫 / 元话语）
- 5 段时长规则（适配 60-90 秒短视频）
- dbs-content 文字洁癖 + 表达效率自检

**使用场景**：
- 长文已定稿，想做条短视频
- 不想自己想钩子和结构

**不做**：
- ❌ **不接多篇素材**（那是 obsidian-publish 的活）
- ❌ **不接单个主题**（用 obsidian-publish 先写成长文）
- ❌ **不写完整口播脚本**（v1 限制，第二阶段 dbs 集成做）
- ❌ 不做 >3 分钟长视频大纲

**条件触发推荐**：
- 钩子段写不好 → 跑 `/dbs-hook` 扩 10-15 条候选
- 写完口播想自检 → 跑 `/dbs-content` 五维诊断
- 要配图 → 跑 codex perbrand

---

### 16.3 publish-to-wechat.sh — **公众号 HTML 渲染 + 剪贴板**

**位置**：`proj04-obsidian-publisher/scripts/publish-to-wechat.sh`

**一句话定位**：长文 markdown → 公众号兼容 HTML + 自动拷到剪贴板，公众号编辑器 Cmd+V 一次搞定。

**输入**：
- markdown 文件路径（必须）
- `--theme`（可选：default / grace / simple / modern，默认 grace）

**输出**：
1. HTML 文件（与 article.md 同目录，如 `article.html`）
2. HTML 自动拷到剪贴板

**命令**：
```bash
bash proj04-obsidian-publisher/scripts/publish-to-wechat.sh /path/to/article.md --theme grace
```

**用户手动操作**（约 10 秒）：
1. 公众号后台新建图文
2. 正文区 Cmd+V

**关键内置能力**：
- 调 baoyu-markdown-to-html（grace 主题 + --cite 外链转底部引用）
- pbcopy 入剪贴板

**2026-06-22 决策**：去掉 opencli weixin create-draft 步骤 — 新建草稿用户自己操作更简单，不需要再删占位文本。

---

### 16.4 post-x-thread.sh — **X 线程发布**

**位置**：`proj04-obsidian-publisher/scripts/post-x-thread.sh`

**一句话定位**：多段文本 → X 线程发布（链式 reply 串）。

**输入**：text 文件，每条推文之间用 `----` 单独一行分隔，推文内部可多行

**输出**：
- 第 1 条 tweet（opencli twitter post）
- 后续每条 reply 上一条（opencli twitter reply）
- 最后打印首条 URL（线程入口）

**命令**：
```bash
bash proj04-obsidian-publisher/scripts/post-x-thread.sh thread.txt
```

**thread.txt 示例**：
```
这是 thread 第 1 条推文。
可以多行。
留悬念，不剧透答案。
----
第 2 条推文，承接第 1 条的悬念。
讲一个具体事件。
----
第 3 条推文，提出反差洞察。
```

**关键内置能力**：
- awk 解析 `----` 分段
- 简单字符权重估算（中文 ×2 + 英文 ×1）超 280 警告
- 失败时断在某条不重试（避免重复发推）
- 失败后打印手动接续指引

**使用场景**：
- obsidian-publish 已生成线程素材，要发出去

**前提**：
- 本机 Chrome 已登录 X / Twitter（opencli 复用 cookie session）

---

### 16.5 codex perbrand — **横版正文配图**

**位置**：`~/.codex/skills/perbrand/`（已存在的 codex skill）

**一句话定位**：长文 markdown → 4-8 张 16:9 彩色手绘正文配图（green-hoodie 主角）。

**输入**：markdown 内容（pipe 进 codex exec）+ 工作目录

**输出**：4-8 张 16:9 PNG 文件（命名按文章语义自动起，如 `01-learning-responsibility.png`）

**命令**：
```bash
cat /path/to/article.md | codex exec \
  -C /path/to/article-dir \
  --dangerously-bypass-approvals-and-sandbox \
  "用 perbrand 默认 green-hoodie 主角给这篇文章生成 4 张 16:9 彩色手绘正文配图，保存到 assets/article-illustrations/" \
  < /dev/null
```

**关键细节**：
- ⚠️ `< /dev/null` 必须有（Codex CLI 在非 TTY 下会 hang）
- ⚠️ `-C <dir>` 设工作目录（配图会保存到这个目录下的相对路径）
- 模型：gpt-image-2（OpenAI 旗舰，2026-04 发布）
- 走 ChatGPT 订阅，不用 OpenAI API key
- 默认 green-hoodie 主角已锁定（perbrand 的 `assets/default-character-green-hoodie.png`）
- 单次 ~$1-2，8 分钟左右

**使用场景**：
- 公众号长文要配图
- 任何需要横版手绘配图的场景

**不做**：
- ❌ 不做封面图（v1 不自动做封面，未来 perbrand × baoyu-cover-image mix）
- ❌ 不做小红书竖版图（小红书 v1 不做）
- ❌ 不锁定其他主角（如要切换主角，需修改 perbrand SKILL.md）

---

### 16.6 dbs 系列 skills — **内容质量诊断 + 钩子优化**

**位置**：`~/.claude/plugins/marketplaces/dontbesilent-skills/skills/`

**一句话定位**：dontbesilent 系列内容创作工具箱，**诊断/优化**导向（不直接生成内容）。

**v1 主线引用的**：
- **dbs-content** — 五维诊断报告（文字洁癖 / 封面标题 / 表达效率 / 认知落差 / AI 辅助）
  - 触发：「这个内容怎么样」「帮我看看文案」「/dbs-content」
  - 输出：诊断报告 + 改进建议
- **dbs-hook** — 短视频开头优化
  - 触发：「优化我的钩子」「这个开头怎么改」「/dbs-hook」
  - 输出：10-15 条钩子候选 + Top 3 推荐
  - **要求**：必须先有正文，没正文不工作
- **dbs-xhs-title** — 小红书 75 标题公式
  - 触发：「帮我起小红书标题」「/dbs-xhs-title」
  - 输出：5-8 个标题（追溯到公式编号）

**其他 dbs skill**（v1 不主用，但可独立调）：
- dbs-action（心理诊断）/ dbs-deconstruct（概念拆解）/ dbs-benchmark（对标分析）/ dbs-diagnosis（商业问题消解）

**关键洞察**（subagent 调研结论）：
- dbs 全系是**诊断/优化导向**，不是**结构化生成导向**
- 不能直接产出短视频大纲、长文等结构化内容
- 但可作为**规则源**被引用（如 short-video-outline 引用 dbs-hook 的 6 类钩子规则）

**使用场景**：
- 写完内容想自检质量 → dbs-content
- 短视频开头不好 → dbs-hook
- 小红书标题想不出 → dbs-xhs-title

---

### 16.7 baoyu-skills — **20+ skill 库**

**位置**：`~/.claude/skills/baoyu-skills/skills/`

**一句话定位**：JimLiu 维护的 22k 星 Claude Code skill 包，含 markdown / 公众号 / 小红书 / X / 翻译 / 图像 / 幻灯片 / 漫画等 20+ skill。

**v1 主线引用的**：
- **baoyu-post-to-wechat / scripts/md-to-wechat.ts** — md → 公众号兼容 HTML（独立 CLI，无 EXTEND.md 依赖）
  - 用法：`bun ~/.claude/skills/baoyu-skills/skills/baoyu-post-to-wechat/scripts/md-to-wechat.ts <article.md> --theme grace`
  - 输出：HTML 文件 + JSON 元数据（title / author / summary / htmlPath）
  - 已被 publish-to-wechat.sh 调用，不需要直接用

**v1 未用但可独立调**（按需查找）：
- `baoyu-markdown-to-html` — 通用 md → 公众号 HTML（4 主题 grace/default/simple/modern，--cite 自动转底部引用，--count 显示阅读时长）
- `baoyu-translate` — 翻译
- `baoyu-youtube-transcript` — YouTube 视频转文本（第二阶段视频/音频转文本能用上）
- `baoyu-slide-deck` — 幻灯片生成
- `baoyu-comic` — 漫画
- `baoyu-diagram` — 图表
- `baoyu-cover-image` — 封面图（未来 perbrand mix）
- `baoyu-xhs-images` — 小红书图片（v1 砍掉，未来重做）
- `baoyu-infographic` — 信息图
- `baoyu-article-illustrator` — 文章插画（不用，配图走 perbrand）
- `baoyu-image-gen` — 通用图像生成
- `baoyu-format-markdown` — markdown 格式化
- `baoyu-post-to-x` / `baoyu-post-to-weibo` — 不用，发布走 opencli
- `baoyu-wechat-summary` — 公众号文章摘要

**关键依赖**：
- Bun runtime（已装 v1.3.11）
- Chrome（CDP-based skill 用）
- baoyu-image-gen / baoyu-cover-image / baoyu-xhs-images 需要 imagegen backend（codex imagegen 已可用）
- 部分 skill 需要 EXTEND.md 配置（按需建）

**使用场景**：
- 公众号 HTML 渲染 → md-to-wechat（已被 publish-to-wechat.sh 包装）
- 翻译 / 转录 / 信息图 → 按 skill 名触发

---

### 16.8 opencli — **跨平台浏览器自动化 CLI**

**位置**：`/usr/local/bin/opencli` (v1.8.0+)

**一句话定位**：143 个 site adapter，通过本机 Chrome 复用 cookie session 完成各平台操作。

**v1 用到的**：
- **opencli twitter post** — 发单条推（已被 post-x-thread.sh 包装）
- **opencli twitter reply** — 回复推文（已被 post-x-thread.sh 包装）
- **opencli twitter search** / **thread** / **profile** — 抓推文 / 看 thread / 看作者粉丝（obsidian-publish 抓社区声音用）
- **opencli reddit search** — 抓 Reddit 帖子（obsidian-publish 用）
- **opencli hackernews search** — 抓 HN 帖子（obsidian-publish 用）
- **opencli weixin create-draft** — 公众号草稿创建（已被 publish-to-wechat.sh 包装）
- **opencli weixin drafts** — 列草稿（验证登录态用）

**v1 未用但有的**：
- `opencli xiaohongshu publish` — 小红书发布（小红书 v1 不做）
- `opencli douyin` / `opencli tiktok` / `opencli weibo` — 抖音/TikTok/微博
- `opencli notion` / `opencli github` / `opencli linkedin` — 其他平台
- `opencli codex` — 控制 Codex Desktop App（不用，直接 spawn `codex exec`）

**关键前提**：
- 本机 Chrome 已登录对应平台（cookie session 复用）
- 部分写操作需要 Chrome 在 foreground

**使用场景**：
- 任何"跨平台浏览器自动化"需求
- 先看 `opencli list` 看 143 adapter 里有没有目标平台

---

### 16.9 决策流程图：未来不清楚用哪个时按这个查

```
我想干什么？
   │
   ├─ 写多平台内容（公众号 + X + 小红书）？
   │  └─→ /obsidian-publish（多素材 or 主题）
   │
   ├─ 把长文做成短视频大纲？
   │  └─→ /short-video-outline <长文>
   │
   ├─ 长文要配横版正文配图？
   │  └─→ codex exec ... < /dev/null（perbrand）
   │
   ├─ 长文要发公众号？
   │  └─→ bash publish-to-wechat.sh <md> --cover <jpg>
   │
   ├─ 多条推文要发线程？
   │  └─→ bash post-x-thread.sh <txt>
   │
   ├─ 内容质量想自检？
   │  └─→ /dbs-content（五维诊断）
   │
   ├─ 短视频开头不好？
   │  └─→ /dbs-hook（10-15 条候选）
   │
   ├─ 小红书标题写不出？
   │  └─→ /dbs-xhs-title（75 公式）
   │
   ├─ 要把 markdown 转成公众号 HTML（不发）？
   │  └─→ bun ~/.claude/skills/baoyu-skills/skills/baoyu-markdown-to-html/scripts/main.ts <md>
   │
   ├─ 要翻译 / 抓 YouTube 转录 / 做幻灯片 / 信息图？
   │  └─→ 看 ~/.claude/skills/baoyu-skills/skills/ 找对应 baoyu skill
   │
   ├─ 要从 X / Reddit / HN 抓数据？
   │  └─→ opencli twitter|reddit|hackernews search|thread|profile
   │
   └─ 不在上面任何一项？
      └─→ 看 opencli list 143 adapter，或在 ~/.claude/skills/ 翻 skill 找
```

---

### 16.10 note-to-xhs — **笔记 → 小红书图文物料（完整工作流）**（2026-06-23 新增）

**一句话定位**：给 1 篇 markdown 笔记，一条龙产出小红书可发物料 = **X 长文样式 3:4 长截图 + 标题 + 正文文案 + 话题标签**。填了 §10 决策表「小红书图片 v1 砍掉、未来重做」槽位。

**触发**：「把这篇笔记发小红书」「这篇做成小红书图文」「/note-to-xhs」「按 X 样式做小红书长截图」「给这篇配标题和文案」

**工作流（4 步，由 `note-to-xhs` skill 编排）**：

| 步 | 做什么 | 用什么 |
|---|---|---|
| 1 渲染 | md → N 张 3:4 长截图（X 长文样式） | `scripts/note-to-xshots.sh` |
| 2 标题 | 75 公式匹配，候选 + Top 3 | 调 `/dbs-xhs-title` |
| 3 文案 | ≤100 字，固定内容风格 | `skills/note-to-xhs/references/caption-style.md` |
| 4 标签 | 核心固定 + 按主题补，8–12 个 | skill 内置 |

**关键文件**：
- 编排 skill：`skills/note-to-xhs/SKILL.md`（软链 `~/.claude/skills/note-to-xhs`）
- **文案内容风格**：`skills/note-to-xhs/references/caption-style.md`（用户定稿风格：开门见山抛反差 → 点破本质 → 对仗金句收尾；0 emoji；不强行加互动钩子；≤100 字）
- 渲染脚本：`scripts/note-to-xshots.sh` + `scripts/render-xshots.ts`
- 模板：`templates/x-longform.html` ｜ 头像：`assets/avatar-linqq.png`（codex perbrand 生成，base64 内嵌进模板）

**底层渲染脚本 note-to-xshots.sh**：
- 用法：`bash scripts/note-to-xshots.sh <note.md> [--banner <图>] [--out <目录>] [--keep-html]`
- 输出：`<out>/01.png …`，每张 **1196×1594（3:4）**
- 标题取笔记**顶部** H1，否则文件名（去末尾日期）；身份固定 = **林锵锵 + 蓝标 + 绿衣丸子头头像**；互动数字随机（评论 100-500 / 转发 1k-5k / 赞 8k-20k / 浏览 1M-8M）
- 图片：`![[img]]` / `![](path)` 按 basename 去 `$OBSIDIAN_VAULT` 递归找 → `file://` 绝对路径，chromium 直接加载（**不丢 vault 图**）
- **智能连续切（黑名单式）**：默认切在 tile 边界、最大化填充；唯一约束「文字不切半行」（文字行设为禁区，切线落入则上移到行顶）；**图片可像长截图一样自由拦腰跨页**；留白极小
- 截图：`playwright-core` 复用已缓存 ms-playwright chromium（无则回退系统 Chrome），零浏览器下载

**技术栈**：Bun + playwright-core + marked（proj04 根目录 `bun add`，有 `package.json` / `node_modules`）

**踩坑（已修，详见 workspace `01_Gotchas.md`）**：① 标题误取正文中段 `#` → 只认顶部 `#` ② `<script>` 无布局盒致 contentBottom=0 → 用最大内容底 ③ Playwright `clip` 大 y 越界 → 改 `scrollTo` + 截视口

**未来（v2）**：自动发布走 `opencli xiaohongshu publish`；圈选打码（用户 2026-06-23 明确 **v1 不需要打码**）

**不做**：不是 Web 工具（终端原生，对齐项目本质）；不改写正文长文（那是 obsidian-publish 的活）；一次只处理一篇

---

**文档结束。**

> 这份文档够一个完全陌生的开发者按图施工。
> 第一版做完后，回来更新本文档（标注哪些 ✅ 完成、哪些遇到坑、哪些工程量估错了）。
> 第二阶段开始前，先回看本文档的"第二阶段"清单 + "不做的事"边界，确认没漂移。
