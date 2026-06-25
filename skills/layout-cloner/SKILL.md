---
name: layout-cloner
description: 克隆任意公众号文章的排版风格，套到用户自己的内容，输出可直接粘贴公众号的 inline-style HTML。两段式——【提取】给一篇喜欢的公众号文章 URL→自动归纳组件架构→渲染预览→确认后存成命名模板；【套用】用某个已存模板把用户的 markdown 渲染成 HTML。触发：「给个链接克隆排版」「提取这篇的排版」「用 XX 模板生成」「layout-cloner」。
---

# 公众号排版克隆器（layout-cloner）

口号：**「给个链接，克隆它的排版」**。用户零门槛、全程不碰代码：给 URL → 看渲染预览点头 → 以后一句话套用。

**Scope：只做公众号文章**（`mp.weixin.qq.com`）。提取靠 `id="js_content"` 正文区，不吃任意网页。

## 两个阶段 + 路由

```
①参考文章 URL ──[提取]──► 命名模板(templates/<名>.json)
                                  │
   ②用户 markdown ──[套用 用名模板]──► output/<标题>-<名>.html ──► 内嵌图 ──► 粘贴公众号
```

| 用户说什么 | 走哪条 |
|---|---|
| 给一篇公众号 URL、要「提取/克隆这篇的排版」 | **提取流程**（下半 §A） |
| 「用 `<某模板>` 把这篇 md 生成/渲染」 + 给内容 | **套用流程**（下半 §B） |
| 给 URL **又**给自己的 md、要「克隆它的排版套到我的内容」 | 先提取存模板、再套用（A→B 串起来） |

**🔒 铁律：模板不得擅自删除。** `templates/<名>.json / -preview.html / .skeleton.html` 都是用户的资产，**只有用户明确要求才删**。

---

# §A 提取流程（LLM 全包）

**正则枚举式提取已退役**——它只认调过的几篇，换个结构就漏（实测一篇标准 h1/h2/p 的文章只提到 2/8 个组件）。现在走 LLM：确定性 prep 把样式facts 摆出来，LLM 只做语义归纳。

```
1. prep   python3 extract_styles.py prep <url> <名>
          → templates/<名>.inventory.txt（每种 tag+style 去重计数）
          + templates/<名>.cleaned.html（清洗后保留嵌套的结构视图）
2. 归纳   subagent 读 上面两个文件 + 本文「提取契约」 → 写 templates/<名>.json
3. 校验   python3 extract_styles.py validate <名>   ← 机器验，不信 subagent 自报
4. 预览   python3 extract_styles.py render <名> → templates/<名>-preview.html → open 给用户
5. 确认   用户看渲染点头 → 留下模板；不对 → 调契约/重抓（回 2）
```

## 提取契约（subagent 归纳时逐条遵守）

读 prep 出的「样式清单 + 清洗结构」，把文章拆成组件，输出**锁死 schema** 的 JSON。每个组件分两类：

- **常规件**（一标签一样式：正文、各级标题、加粗/高亮/下划线、行内代码、代码块、列表、引用）→ `{description, tag, style:{扁平css}, sample}`
- **复合件**（一个盒子里有内部布局 + 多个内容位置：封面卡、横滚目录、分节头、提示/CTA 卡、作者条）→ `{description, skeleton:"含{{槽位}}的HTML", slots:{槽位:{from,when,example,is_image?}}, structure_rules:[...], sample}`

### 5 条铁律（每条都是实测栽过的）

1. **★ 根容器必提**。提一个 `container` 组件，抓最外层的基础样式（`font-size / font-family / color / line-height / letter-spacing`）。**正文和绝大多数文字的字体字号是继承根容器的**——正文 `body_text` 的 style 里通常**没有**字体。漏了根容器，套出来正文字体字号全错。
2. **★ 分节头要成组**。标题前若有**编号 / 装饰图 / 大数字**（如「01.」），把「编号 + 标题 + 副标题」当**一个复合件**，别拆成游离的图+文字。
3. **★ box-sizing 全补**。复合件 skeleton 里**每个带 `border` 或 `padding` 的块级容器都补 `box-sizing:border-box`**，一个别漏。flex 容器保持 flex，不许降级成 inline。
4. **★ 语义闸门**。带内容语义的装饰字（`STEP`/步骤/第N步/序号前缀）→ 做成**带闸门的槽位**（默认只放数字，除非内容本身有步骤语义才加前缀字），**不要写死成固定结构**。纯版式标签（与内容无关的 `PART`/章节名）才保留为结构。
5. **★ 图类：抓住原图地址 `src` + 标 `is_image`，用不用交给用户**。
   - 图片（编号图、配图、**图片化的标题 / 分节头 / 整版设计图**，很多公众号把大标题直接做成 PNG）对应槽位标 `"is_image": true`，并把**原图真实地址抓进 `"src"` 字段**（prep 已把公众号的 `data-src` 转成 `src` 保住了——**别丢**）。
   - 图片化的标题 / hero 登记成**单独组件**（如 `hero_image`），别和正文配图混成一类。
   - `structure_rules` 注明：**图里的文字 / 设计是焊死在像素里的**——套你自己内容时这张图带的是**参考文章的字**。所以它是个「图槽位」：复刻同篇 → 可嵌原图；套新内容 → 需换你自己的图（或拿它当参照重做）。**提取只负责抓住、保留；用不用是套用时用户决定。**
   - ⚠ **边界**：本 skill 克隆的是 **CSS 排版**。一篇文章若视觉设计主要在图片里，能克隆的 CSS 很薄——如实提取那薄层 + **抓住图地址** + 标 `is_image`，别假装能用 CSS 重现图片设计。预览自动：抓到地址就显示**参考原图**、否则占位，并打 ⚠ + 顶部摘要。

### 另外几条

- **标题可能不是 `<h1>/<h2>`**——很多公众号用「大字号加粗的 `<p>`/`<section>`」当标题。**按视觉角色认**（字大/加粗/独占一行），别只看标签名。
- **不要无中生有**：文章没有的组件别造（朴素文章就如实只提正文+几种强调+标题）。
- **inline 样式值逐字照抄**，别改写、别归一化。`sample`/`example` = 本文样例文字，**仅供认组件、绝不进产出**。
- 顺序大致按文章从上到下。

### 🔒 锁死的 JSON schema（顶层扁平，不许包 `components` 外壳）

```jsonc
{
  "_meta": { "style_name": "...", "source_url": "...", "article_type": "...", "visual_style": "一句话风格" },
  "container":   { "description": "...", "tag": "section", "style": { "font-size": "15px", "font-family": "...", "color": "...", "line-height": "..." }, "sample": "" },
  "body_text":   { "description": "...", "tag": "p", "style": { ...扁平... }, "sample": "本文样例" },
  "heading_h1":  { "description": "...", "tag": "...", "style": { ... }, "sample": "..." },
  "cover_card":  {                                              // 复合件
    "description": "...",
    "skeleton": "<section style='...flex/box-sizing...'>...{{TITLE}}...{{DATE}}...</section>",
    "slots": { "TITLE": {"from":"文章标题","when":"总有","example":"<参考标题>"},
               "NUMBER_IMAGE": {"from":"序号图","when":"总有","example":"<img>","is_image": true} },
    "structure_rules": ["哪里必须 flex / box-sizing", "is_image 的复用说明"],
    "sample": "..."
  }
}
```
**硬约束**：顶层就是 `_meta` + 各组件（**不要**再包一层 `components`）。**必有** `_meta`、`container`（带字体）、至少 1 个正文件、至少 1 个标题件。

### 校验（机器验，不信自报）

`validate` 子命令会查：JSON 合法 → 顶层 schema 对（无 `components` 外壳）→ 必备组件齐（container 带字体 / 正文 / 标题）→ 每个 skeleton 的 `{{槽位}}` 都在 slots 里有定义、带 border/padding 的块都有 box-sizing。**任何 subagent 自报「我提了 X」都要用它复核**——实测自报屡次和实际不符。

---

# §B 套用流程（把模板套到用户内容）

`subagent 读 templates/<名>.json + 用户 md，按下面契约逐段套成 HTML → output/<标题>-<名>.html`。

套样式 = 拆成两层：**结构（骨架）忠实保留** + **内容（槽位）来自用户文本**。

## 🔴 铁律一：内容只来自用户文本

参考文章里每一处具体文字——序号前缀、日期、作者名、标签词、英文副标——都是**那篇的示例内容**，不是样式，**绝不能冒进产出**。每处文字当成槽位，填前三问：

1. **来源**：用户 md 哪段文字填这里？映射不到 → 省略该槽位/组件。
2. **条件**：这组件/槽位何时才该出现？
3. **语义闸门**：位置带语义（步骤号/日期/作者/分类）→ 用户文字必须真有这个语义，否则换写法/留空——不硬塞参考的语义字。序号胶囊只放数字，无步骤语义不出 `STEP`。
- **通用兜底**：模板里 `sample`/`example` = 参考示例，**仅认组件、绝不进产出**。`is_image:true` 的图槽位**由用户决定**：复刻同篇 → 嵌入模板存的原图 `src`；套你自己的新内容 → 换成用户自己的图 / 留占位 / 拿原图当参照重做（**图里带的是参考文章的字，直接搬到你的新内容上字是错的**）。默认问用户、不擅自塞原图。
- `default` 字段（如平台三连引导语）才是允许直出的常量。

## 🔵 铁律二：结构忠实保留

- 简单组件 → 把用户 md 元素**包上该组件的 `style`**（正文段落包 body_text 的 style，md `## 标题` 包对应 heading 的 style，``code`` 包 inline_code…）。**别忘了最外层套 `container` 的基础样式**（字体字号从它继承）。
- 复合组件 → **整段复制 `skeleton`**，只把 `{{槽位}}` 换成用户内容；flex 保持 flex、带 border/padding 的块保持 `box-sizing:border-box`，一个属性都不许降级/丢失。
- 图片 `![[x.png]]` → `<img src="x.png" …>`（src 只放文件名，inline-images.py 从 vault 抓）。

## ✅ 出稿前自检（没过不许交）

```
结构  [ ] 最外层套了 container 基础样式？正文字体字号对？
      [ ] flex 容器仍是 flex、没降级成 <p>+inline？带 border/padding 的块都有 box-sizing？
      [ ] 带 skeleton 的组件整段复制、没漏属性？
内容  [ ] 产出里搜不到任何参考示例字（sample/example 的值）？
      [ ] 序号胶囊只有数字（除非用户内容真含步骤语义）？日期/作者/标签都映射到了用户内容？
      [ ] is_image 的图按用户内容处理了、没直接搬原文图？
```
机器自检：把模板所有 `sample`/`example` 值收集成「禁出现」清单，断言一个都没泄漏进产出（脚本见旧版，与风格无关）。

---

# 命令速查

```bash
# 提取（阶段 A）
python3 skills/layout-cloner/extract_styles.py prep <url> <名>     # → inventory + cleaned.html
#   （subagent 读 prep 产物 + 本文提取契约 → 写 templates/<名>.json）
python3 skills/layout-cloner/extract_styles.py validate <名>        # 机器校验 schema/必备件/box-sizing
python3 skills/layout-cloner/extract_styles.py render <名>          # → templates/<名>-preview.html
#   （open 预览给用户确认）

# 套用（阶段 B）：subagent 读 templates/<名>.json + 用户 md，按 §B 契约套 → output/<标题>-<名>.html
# 发布：bash scripts/publish-to-wechat.sh <html>   # 图 base64 内嵌 → 粘贴公众号
```

> `templates/<名>-preview.html` 是给用户看的**可视化预览**（组件清单画廊）；`.json` 是机器读的样式数据（用户不看）。复合件可把骨架另存 `<名>.skeleton.html` 并在 JSON 用 `skeleton_ref` 引用，简单件只留 `style`。
