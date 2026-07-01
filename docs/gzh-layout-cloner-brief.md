# Skill 启动说明：公众号排版克隆器（gzh-layout-cloner）

> 给新 session：你没有上一个 session 的上下文。读完这份就能开工——这里是全部需要知道的。

## 一句话目标

做一个 skill：**用户给一篇喜欢的公众号文章 URL，AI 克隆它的整套排版风格，套到用户自己的 markdown，输出可直接粘贴公众号的 HTML。**
口号：「给个链接，克隆它的排版」。

## 铁律：用户零门槛，全程不碰 HTML

用户只做两件事：① 给 URL ② 看渲染预览点头。
解析 HTML、扒 inline style、归纳组件——**全是 AI 干**，用户永远看渲染效果，不看代码。

> ⚠️ 反面教材：上个 session 是让用户**手动挑组件 HTML 发过来**的（金句卡、代码块都是用户贴的代码）。那是对话里图快，**绝不要这么设计 skill**——目标用户不懂 HTML。

## skill 流程（5 步）

1. 用户给参考文章 URL
2. AI `curl` 抓 HTML（后台，用户不可见）
3. AI **自动**解析归纳所有组件 + 精确 inline style：
   - 各级标题、正文、强调（加粗/下划线/亮色底）、代码块、图片（含 padding 等所有细节）、特殊组件（卡片/标签/横滚目录等）
4. AI 把组件**渲染成可视化预览**给用户看 → 用户确认/调（看效果，不看 HTML）
5. 生成「样式系统」（inline 样式速查表 + 套用规则）→ 套用户 md → HTML（走 subagent 隔离）
   - 样式系统可保存复用：给风格起个名，下次同风格直接套，不重新提取

## 现成蓝本（基于这些做，别从零摸索）

上个 session 已经把这套流程**手动跑通过一遍**，产物都在 proj04：

- **`templates/wechat-green.html` = 提取产物的范例**。这就是 skill 要自动生成的那种「样式系统」。它从 `https://mp.weixin.qq.com/s/qGdmYj-3B9AB8TTu2vSWFw` 提取，含：容器 / 正文 / 三强调(绿加粗·黄金底 #FDE68A·绿下划线 #A7F3D0) / 一级大数字标题(数字+竖线+中英) / 二级黑粗+绿竖条标题 / 横滚目录卡 / 金句卡(虚线框) / 标签胶囊 / Mac 代码块 / 图片。**先精读它，理解「样式系统」长什么样。**
- **套样式 + 发布流程现成**：`scripts/publish-to-wechat.sh` + `scripts/inline-images.py` 把套好的 HTML 里的图 base64 内嵌（图片自动从 Obsidian vault 抓）。直接复用。
- **套样式做法**：`skills/obsidian-publish/SKILL.md` 的「发布」段 + `references/wechat-green-publish.md`，有「Claude 读样式表逐段把 markdown 套成 HTML」的现成 prompt 思路（上个 session 用 subagent 跑的）。

## 第一个测试用例

- 参考文章：`https://mp.weixin.qq.com/s/qGdmYj-3B9AB8TTu2vSWFw`（《7个Agent + 我，两天做了款能上架的 AI 游戏》）
- 用户 md：`/Users/doushun/本地文稿/Obsidian Vault/【1】WAY2AI/【1.4】output/AI时代最大的幻觉.md`（无 frontmatter，14 张图，4 个一级标题 #，5 个二级 ##）
- 验收标准：skill 自动提取 + 套出来的效果，≈ 上个 session **手动**提取（wechat-green.html）的质量

## 唯一真难点 + 兜底

| 难点 | 兜底 |
|---|---|
| 公众号 HTML 噪音极多（嵌套 section + `<span leaf>`），AI 自动归纳**可能漏组件 / 抓错样式** | 提取后**渲染预览给用户确认**，不对就重抓。用户始终看渲染、不看代码 |
| 复杂组件（横滚卡）泛化成模板要判断哪些是内容、哪些是结构 | 同上，预览迭代 |

**更精确的可选项**：用 playwright 打开文章读每个元素的 computed style（浏览器算好的精确值），比 curl 解析更准。但 gstack 的 `browse` 现在缺 chromium，要先修（`playwright install chromium` 或 browse 的 setup）。

## 技术路径（建议）

- **抓取**：`curl` + Safari UA（公众号是公开页，能拿完整 inline style HTML，已验证）
- **解析**：取正文 `id="js_content"` 区域，清洗噪音后喂 LLM，让它归纳组件 + 提取每个 inline style
- **预览**：生成样例 HTML，`open` 给用户看
- **套 md**：subagent 读样式系统 + 用户 md，逐段套（参考 obsidian-publish 的套样式 prompt）
- **内嵌发图**：复用 `publish-to-wechat.sh` + `inline-images.py`

## 怎么开工

1. 开分支：`cd ~/Desktop/workspace/proj04-obsidian-publisher && git checkout -b feature/layout-cloner`
   - **在 proj04 内开发**（复用现成脚本/蓝本，别新建独立项目）。skill 文件放 `skills/gzh-layout-cloner/`，跟 `obsidian-publish` 并排；做好后 symlink 到 `~/.claude/skills/gzh-layout-cloner`（参考 obsidian-publish 的 symlink 做法）。
2. 精读 `templates/wechat-green.html`（理解目标产物）
3. **第一步只做「常规组件自动提取」**：curl qGdmYj 文章 → 让 AI 自动扒出 标题/正文/强调/图片 的 inline style（先不碰复杂卡片）→ 渲染预览 → 跟 wechat-green.html 对比，看自动提取够不够准
4. 准了，再加复杂组件（卡片/横滚目录）的提取
5. 最后串成 skill：URL → 提取 → 预览 → 套 md → HTML

## 不要做的

- ❌ **【最致命】不要硬编参考文章的「示例内容」**——严格分离**样式**(保留) vs **内容**(来自用户文本)。典型坑：黑胶囊的样式可以留，但里面写死 `STEP 01` 就错了——`STEP` 是参考文章的示例字；用户文本里是「第一个方法 / 1.」，没有「步骤 / STEP」语义就**绝不能冒出 STEP**。同理：日期、作者名、品牌名、标签文字、英文副标题，**全部从用户的内容来，不是从参考文章抄**。提取组件时，把每个文字位标记成「内容槽位（待用户文本填）」而非固定值。**这是整个 skill 最容易犯、也最毁质量的核心错——主 session 已经栽过两次（STEP 硬编、日期没对齐），务必在套样式逻辑里专门盯。**
- ❌ 不要让用户挑 HTML 组件（用户不懂 HTML，这是整个 skill 的反面）
- ❌ 不要纯靠截图视觉提取（拿不到精确 padding/字号/颜色值；截图只能辅助识别「有哪些组件」，精确样式必须从 HTML/computed style 拿）
- ❌ 颜色等细节要忠实参考；但如果用户指定主题色，按用户的（上个 session 是「颜色不变」保持绿 #00a86b）

---

**背景补充**：proj04 是「Obsidian 笔记 → 公众号/小红书/X 发布工作流」（独立 git repo，非 home repo）。这个 gzh-layout-cloner 是它的自然延伸——把「固定一套绿色样式」泛化成「克隆任意参考文章的样式」。`wechat-green.html` 就是从绿色那一套手动做出来的第一个实例。
