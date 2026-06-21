# proj04-obsidian-publisher

> 把 Obsidian 笔记一键改写成适配多平台（公众号 / X 线程 / 小红书卡片图）的内容工具。

创建：2026-06-18

---

## 一、产品定位（已确认）

- **谁用**：自己用，留扩展余地（暂不做商业化、不做多用户）
- **数据源**：Obsidian vault
- **核心价值**：同一份笔记，自动改写成不同平台的风格 / 格式 / tag
- **不做**：内置发布（交给 opencli 等外部工具）

## 二、第一版范围（已确认）

| 平台 | 输出形态 | 备注 |
|------|----------|------|
| 微信公众号 | 长文 HTML | 公众号编辑器吃 HTML 不吃 markdown |
| X (Twitter) | 多条推文线程 | 每条 ≤280 字符，自然衔接 |
| 小红书 | 多张卡片图 PNG | 封面 + N 张内容卡 |

**第二版**：朋友圈短文、X 长文、TikTok/抖音脚本、Obsidian 文件浏览器（选参考资料）

## 三、产品形态（已锁定 2026-06-18）

**本地 Web 工具**（Node 后端 + 浏览器前端）：

```
[Obsidian vault 文件夹]（本地 fs 直接读）
        ↓
[Node 后端] ←─→ [浏览器 UI @ localhost:7777]
   ├→ LLM 改写（Claude / OpenAI API）
   │    ├→ 公众号 HTML
   │    └→ X 线程
   ├→ HTML 模板 + Playwright 渲染 → 小红书卡片 PNG
   └→ 子进程调 opencli 发布
        ├→ opencli twitter post（X 线程）
        ├→ opencli weixin create-draft（公众号草稿）
        └→ opencli xiaohongshu publish（小红书图文）
```

**为什么不是 Obsidian 插件**：
- opencli 已覆盖发布，不需要插件接平台 API
- 数据源是普通 markdown 文件，Node fs 直接读即可

**为什么不是 Chrome 扩展**：
- Chrome 沙箱读不了本地 vault 文件夹
- Chrome 沙箱调不了本地 opencli 命令
- 用 Native Messaging 绕过反而更复杂

**为什么不是纯 CLI**：
- 用户明确要可视化 + 浏览器内体验
- 后期可套 Electron 变桌面 App

## 四、opencli 调研结果

| 平台 | 命令 | 验证 |
|------|------|------|
| X | `opencli twitter post <text>` | ✅ 文档原文"Post a new tweet/thread" |
| 公众号 | `opencli weixin create-draft <content>` | ✅ 创建图文草稿 |
| 小红书 | `opencli xiaohongshu publish <content>` | ✅ Creator center UI automation |

opencli 全部用 Browser Bridge（真实浏览器自动化），共享登录态，不踩官方 API 限制。

## 五、验证方式（已确认）

发到「公众号草稿箱 + 个人小号（X / 小红书）」，不动主账号。

## 五、下一步

1. 用户拍板产品形态 + opencli 澄清
2. **GitHub 复用扫描**，目标清单：
   - `obsidianmd/obsidian-sample-plugin`（官方插件脚手架）
   - Obsidian → 公众号（如 `sunbooshi/note-to-mp`）
   - Obsidian → X/Twitter 线程类插件
   - 小红书卡片图模板（HTML 模板 + Playwright 渲染）
3. 功能定稿后，按 [2026-06-15 AI-news 第一篇](../../本地文稿/Obsidian%20Vault/【1】WAY2AI/AI-news/2026-06-15.md) 设计本项目专属 skill 体系

## 六、开源复用决策（2026-06-18 GitHub 调研结论）

| 赛道 | 决策 | 备注 |
|------|------|------|
| 公众号 HTML | ✅ 直接用 [`md2weixin-core`](https://www.npmjs.com/package/md2weixin-core) | `npm install` 调 `getHtml()` 即可。配合抄 `sunbooshi/note-to-mp` 的 inline-css 当样式素材 |
| 公众号 Gotchas | 📖 参考 `vigorX777/wechat-article-formatter` | 当公众号兼容规则手册读，不引代码 |
| X 线程切分 | 🤖 Claude prompt 切 + [`twitter-text`](https://github.com/twitter/twitter-text) 校验 | OSS splitter 全死，没现成可用 |
| 小红书卡片 | 🛠️ 自己写（1 天）：Tailwind 模板 + [`node-html-to-image`](https://github.com/frinyvonnick/node-html-to-image) | 没有可直接调的库；guizang 是 LLM skill 且 AGPL，只抄设计规范 |
| 小红书设计灵感 | 📖 参考 `op7418/guizang-social-card-skill` 的 `references/` | 只看不引（避免 AGPL） |

## 七、技术栈

```
Node 后端 (Express / Fastify)
├── 读 vault: fs.readdir
├── LLM 改写: @anthropic-ai/sdk
├── 公众号 HTML: md2weixin-core
├── X 线程: Claude prompt + twitter-text 校验
├── 小红书卡片: Tailwind 模板 + node-html-to-image
└── 发布: child_process → opencli

前端 (Vite + React/Vue)
├── 左：vault 文件树
├── 中：文章预览
└── 右：3 平台改写结果 + 操作按钮
```

## 八、决策日志

- **2026-06-18**：项目启动，确认范围（公众号长文 / X 线程 / 小红书卡片图）
- **2026-06-18**：架构 v1（Obsidian 插件 + 本地服务）→ 因 opencli 已覆盖发布 → v2（本地 Web 工具）
- **2026-06-18**：完成 GitHub 复用扫描，三赛道决策已定（见上）
