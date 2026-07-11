# Layout-Cloner 移交文档

> 给新 session：读完这份就能接手。

## 项目位置

```
/Users/doushun/Desktop/workspace/proj04-obsidian-publisher
分支: feature/layout-cloner
最新提交: 6f39c41
```

## 一句话背景

proj04 是「Obsidian 笔记 → 公众号发布」的工作流项目。gzh-layout-cloner 是它的子功能：**给一篇公众号文章 URL，自动提取排版风格，套用户的 markdown，输出可粘贴公众号的 HTML。**

## 目录结构

```
skills/gzh-layout-cloner/
  extract_styles.py        # 核心脚本：URL → 提取组件样式 → JSON + preview HTML

templates/                 # 每个风格 3 个文件：.json（样式数据）、.html（样式速查模板）、-preview.html（可视化预览）
  绿色科技风.json / -preview.html   # section 嵌套型，绿色主题 #059669
  秀米招聘风.json / -preview.html   # xiumi 型，蓝边框+绿阴影 neo-brutalist
  瑞幸报纸风.json / -preview.html   # textstyle span 型，多色块标签报纸风
  wechat-green.html                 # 手动做的第一版绿色模板（蓝本参考）

output/                    # 套样式产出的 HTML
  AI时代最大的幻觉-绿色科技风.html   # ⚠️ 封面卡片右边框 bug
  乙方风格测试-秀米招聘风.html       # ✅ 正常
  乙方风格测试-瑞幸报纸风.html       # ✅ 正常

docs/
  gzh-layout-cloner-brief.md            # 完整的 skill 设计文档（目标、流程、技术路径）
```

## ✅ 已根治：套样式逻辑的 3 个通病（2026-06-25 完成；原「回来第一件事」）

> **根治方式**：
> - 新增 `skills/gzh-layout-cloner/SKILL.md` —— 套样式**执行契约**（之前 gzh-layout-cloner 根本没有 SKILL.md，套样式无成文规则，所以每跑一篇都重犯）：铁律一「内容只来自用户文本」+ 槽位三问/语义闸门，铁律二「结构忠实保留」+ flex/box-sizing 防降级，外加出稿前自检闸门 + 通用泄漏自检脚本。**全程风格无关**（不写死任何具体风格/参考内容）。
> - 复杂组件改「骨架 + 槽位」：骨架存 `templates/<风格名>.skeleton.html`（真 HTML，已含正确 flex / box-sizing），JSON 带 `skeleton_ref` + `slots`（每槽位标 来源/条件/语义闸门）。套样式 = 整段复制骨架、只换 `{{槽位}}` → 结构不可能再降级。
> - `tag_step` 更名 `heading_index_pill`（连 extractor 一起改）：胶囊里只放**序号数字**，无步骤语义不出 STEP。`sample/example` 字段明确标注「仅认组件、禁进产出」。
>
> **验证**：盲跑 subagent（只给 SKILL.md 契约 + 绿色模板 + 用户 md，**不看手动修版**）重生成 `output/AI时代最大的幻觉-绿色科技风.regen.html` —— 三个 bug 区与手动修版**逐字一致**（封面 box-sizing、flex 眉题弹性线、序号胶囊 `01`），STEP=0、box-sizing×13、零参考内容泄漏。即「换个没看过答案的人、照契约也能做对」。
>
> 差异（非 bug，属内容裁剪/模板完整度）：盲跑把导言切成 4 个 part（手动版 5 个）、未复现金句卡——因金句卡/Tips/居中公式这些组件**手动版手搓、模板尚未正式收录**。要让产线自动产出同等丰富度，下一步把这几个组件补成正式 slotted 组件即可。
>
> 下面原始记录保留备查。

---

### （原始记录）主 session 2026-06-24 发现的 3 个通病

主 session 帮用户验收 `output/AI时代最大的幻觉-绿色科技风.html` 时，发现 **3 个 bug，已全部在该 output 文件里手动修好（当正确写法的参照）**。但它们都是**套样式那一步的通病**，治标不治本——下篇新文章 / 别的风格还会重犯。**回来后照这张表根治「模板套用户 md」的逻辑：**

| # | 现象 | 根因 | 根治方向 |
|---|---|---|---|
| ① 内容硬编（最致命） | 二级标题胶囊硬塞 `STEP 01`，但文本是「第一个方法 / 1.」、没步骤语义 | 把参考文章的**示例内容**当固定值套了 | 每个文字位是**内容槽位**，从用户文本填。按文本判断：没步骤语义不带 STEP；真教程才带步骤。日期 / 作者 / 标签 / 英文副标题同理，全从用户内容来，不抄参考 |
| ② flex 退化 | 封面眉题行日期不靠右 | 模板的 `flex 容器 + flex:1 弹性线` 被套成 `<p> inline + 固定宽线` | 套样式**忠实保留模板 flex 结构**，不降级成 inline |
| ③ box-sizing 丢失 | 封面卡片右边框被容器裁掉 | 带 `border + width:100%` 的容器丢了 `box-sizing` | 任何带 border/padding 的块级容器，**默认补 `box-sizing:border-box`** |

**共性**：套样式既要保模板**结构**（flex / box-sizing），又要把**内容槽位**填成用户文本（不抄参考示例）。内容分离铁律见 `docs/gzh-layout-cloner-brief.md` 的「不要做的」第一条。

**注意**：`output/AI时代最大的幻觉-绿色科技风.html` 已被主 session 改过（3 处修复），`git status` 会显示它变了——拿它对比你原来生成的，就能看到正确写法。

---

## （原）待修 Bug 详情：绿色科技风封面卡片右边框缺失（= 上表 ③，已修）

**文件**: `output/AI时代最大的幻觉-绿色科技风.html`

**现象**: 封面卡片左边有圆角绿边框，右边没有。绿色作者条（WAY2AI + 标签）向右溢出。

**卡片结构（当前）**:
```html
<!-- 外层卡片 -->
<section style="margin:0 0 32px;background:#fff;
  border:1.5px solid rgba(5,150,105,0.15);
  border-radius:20px;overflow:hidden;
  box-shadow:0 4px 20px rgba(0,0,0,0.06);width:100%;">

  <!-- 标题区 -->
  <div style="padding:32px 28px 28px;">
    ...标题内容（已修好）...
  </div>

  <!-- 绿色作者条 ← 这里溢出 -->
  <section style="background:linear-gradient(135deg,#059669,#10B981);
    padding:12px 28px;display:flex;align-items:center;
    justify-content:space-between;box-sizing:border-box;width:100%;">
    <p>WAY2AI</p>
    <section style="display:flex;gap:4px;">
      <span>Satya Nadella</span>
      <span>人力资本</span>
      <span>Token资本</span>
    </section>
  </section>
</section>
```

**已尝试**:
1. 去掉封面图占位的 flex 双栏 → 标题区修好了
2. 给绿色条加 `box-sizing:border-box;width:100%` → 没解决

**可能的方向**:
- 检查浏览器渲染时 `overflow:hidden` 是否对 `<section>` 嵌套生效（公众号编辑器和普通浏览器渲染可能不同）
- 尝试把绿色条改成 `<div>` 而非 `<section>`
- 尝试给绿色条加 `max-width:100%;overflow:hidden`
- 或者参考原文的精确 HTML 结构——原文来源是 `https://mp.weixin.qq.com/s/qGdmYj-3B9AB8TTu2vSWFw`，搜索 `linear-gradient(135deg,#059669` 可以找到原文的封面卡片实现

## 本次 session 做的改动总结

### extract_styles.py 修了 4 个 bug

| Bug | 修复 | 位置 |
|-----|------|------|
| 秀米正文色被误判为绿色（装饰色频率最高） | 从 `<span leaf=>` 内容层推断正文色，不用全局 color 频率 | `_extract_xiumi_all()` |
| 漏提 border+box-shadow 卡片框架 | 新增 `card_frame` 提取，识别 border+shadow 组合 | `_extract_xiumi_all()` |
| 图片黑框首次提取失败（瑞幸） | 正则扩展支持 `border: Npx solid` 简写 | `_extract_image()` |
| 分隔条误匹配窄装饰元素 | 增加 width 过滤，跳过 <50px 的元素 | `_extract_xiumi_all()` |

### extract_styles.py 新增的组件类型

- `card_frame` — border + box-shadow 组合卡片（秀米核心视觉）
- `brand_label` — 品牌标签药丸（背景色+对比文字色）
- `separator_bar` — 分隔条（小高度+背景色+可选边框）
- `cta_bar` — CTA 区块（大面积背景色+粗边框）
- 大标题现在保留 `text-shadow` 属性

### 模板更新

- **秀米招聘风**: 完全重写 JSON + HTML + preview。核心视觉：`border:4px solid rgb(48,66,202)` + `box-shadow:rgb(1,229,152) 4px 4px 0px` + 灰底 `rgb(248,248,248)` + 14px 黑字
- **绿色科技风**: JSON 和 preview 新增 `cover_card`（顶部封面卡片）和 `footer_triple_action`（底部三连引导 SVG 图标）
- **瑞幸报纸风**: 未改动

## 跑提取脚本

```bash
cd /Users/doushun/Desktop/workspace/proj04-obsidian-publisher
python3 skills/gzh-layout-cloner/extract_styles.py <URL或本地HTML> [风格名]

# 示例
python3 skills/gzh-layout-cloner/extract_styles.py https://mp.weixin.qq.com/s/YSjRfTJZ8cR2DhrtsufBqQ 秀米招聘风
# 输出: templates/秀米招聘风.json + .html + -preview.html
```

## 参考文件

- `docs/gzh-layout-cloner-brief.md` — 完整 skill 设计（目标、流程、铁律、技术路径）
- `templates/wechat-green.html` — 手动做的第一版模板（理解「样式系统」长什么样的蓝本）
- `scripts/inline-images.py` — 图片 base64 内嵌（产出 HTML 里图片路径是本地绝对路径，需要跑这个脚本才能在公众号用）
