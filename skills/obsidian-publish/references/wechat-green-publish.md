# 公众号绿色发布流程（定稿后）

> ⚠️ **2026-06-28 两处更正**：
> ① **Step 3 套样式已改**——不再用已删除的 `templates/wechat-green.html`，改用 **layout-cloner §B 套 `绿色科技风`**（用户公众号品牌模板：封面 @林锵锵 头像 + art2 灰盒代码块 + harness 引用框）。
> ② **Step 1 配图生成后必须立即做 Step 2 回写插图**——codex 只产 PNG+shotlist，不会自动插回文章；别停在生成。

文章在 obsidian-publish 创作定稿后（通常是 Obsidian vault 笔记）走这套发布到公众号。
图片**全部 base64 内嵌**，粘贴公众号编辑器时会自动上传素材库——已实测可行。

## 顺序

```
定稿笔记 →（配图，明确指令才触发）→ 发布副本+插入 → 套绿色样式 → 内嵌 → 粘贴
```

---

## Step 1：perbrand 配图（明确指令才触发）

⚠️ **生图花钱**（gpt-image-2 每张有成本），且耗时几分钟。**只在用户明确说「配图」时触发，绝不自动。** 文章必须先定稿。

```bash
bash scripts/illustrate.sh <vault笔记.md>          # 默认 4-8 张
bash scripts/illustrate.sh <vault笔记.md> --count 5 # 指定张数
bash scripts/illustrate.sh <vault笔记.md> --dry-run # 不花钱看 prompt
```

产出（文章同目录，即 vault 内）：
- `<笔记名>-illustrations/<笔记名>-perbrand-01.png …` — 配图（**带笔记名前缀，避免 vault 内多篇同名冲突**）
- `<笔记名>-shotlist.md` — 每张：文件名 / 位置锚点（文章精确原句）/ 画面 / 概念
- `<笔记名>-illustrate.log` — codex 完整输出（隔离，不进上下文）

**如果用户只用自己的截图、不要 perbrand 配图 → 跳过这步。**

---

## Step 2：发布副本 + 插入配图

1. **复制**原笔记 → `<笔记名>-publish.md`（⚠️ 原始沉淀笔记**不动**）
2. 读 `<笔记名>-shotlist.md`，按每张的「位置」锚点（文章精确原句）在副本里找到那句，把 `![[<笔记名>-perbrand-0N.png]]` 插在其后
3. 原有的截图引用 `![[截屏xxx.png]]` **保留原位**
4. 副本现在图文完整（perbrand 配图 + 截图），可在 Obsidian 直接预览

> 插入用 Claude 语义判断位置（锚点常是自然语言，如「飞轮段落前」），不要纯脚本匹配。

---

## Step 3：套绿色样式 → 绿色 HTML

⚠️ **已改用 layout-cloner**（`templates/wechat-green.html` 已删）：用 layout-cloner §B 把副本 markdown 套成 `绿色科技风` HTML（见 SKILL.md『发布』段路径 A）。下面这套手搓「样式速查表」仅作历史参考：

| markdown | → 绿色 inline 样式（见模板） |
|---|---|
| 段落 | `<p style="…">` |
| 标题 | `<h3 style="…绿色左边框+底色…">` |
| 引用 | `<blockquote style="…绿色四边框…">` |
| 金句/公式 | 居中大字 `<p style="…#00a86b…">` |
| 重点词 | `<strong style="color:#00a86b">` |
| `![[xxx.png]]` | `<img src="xxx.png" …绿色边框…>`（src 只放文件名，inline 会从 vault 抓） |

保存为 `<笔记名>-wechat.html`。

---

## Step 4：内嵌 + 拷贝

```bash
bash scripts/publish-to-wechat.sh <笔记名>-wechat.html          # PNG 无损
bash scripts/publish-to-wechat.sh <笔记名>-wechat.html --jpeg   # 体积压 ~5x
```

`inline-images.py` 把所有本地图转 base64 内嵌：
- perbrand 配图：相对路径 `<笔记名>-illustrations/…` 或从 vault 按名抓
- 截图：`OBSIDIAN_VAULT` 自动递归搜（默认 `/Users/doushun/本地文稿/Obsidian Vault`）

产出 `<笔记名>-wechat-publish.html` + 内容已进剪贴板。

---

## Step 5：粘贴

公众号后台 → 新建图文 → 正文区 **Cmd+V**（base64 图自动上传素材库）。

体积：PNG 默认，10 张图约 5-6MB；粘贴卡就重跑加 `--jpeg`（约 1MB）。

---

## 关键约束（铁律）

- **配图绝不自动**——只有用户明确说「配图」才跑 illustrate.sh（花钱）
- **发布副本不污染原始沉淀笔记**——所有配图引用、渲染产物都在副本/衍生文件上
- **配图文件名带 `<笔记名>-` 前缀**——否则 vault 内多篇 `![[perbrand-01]]` 会歧义、inline 抓错图
- **绿色路线只管公众号**——小红书走 `note-to-xshots.sh`（X 长文风 → 3:4 截图，见发布段路径 B / `REQUIREMENTS.md` §16.10），X 线程走 opencli
