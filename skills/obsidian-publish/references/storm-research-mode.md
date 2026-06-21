# STORM 研究模式（路径 B：1 主题 → 1 篇文章）

> **何时读这个文件**：用户**只给 1 个主题**（没给素材）+ **明示**要做研究时启用。
> **核心机制**：跑 STORM 4 个独立 prompt → 输出 briefing → 作为 Step 1 的"素材"无缝接入路径 A 的 5 步流程。
> **来源**：Stanford OVAL Lab 在 NAACL 2024 发表的 STORM 论文 + @heynavtoor 的 4 prompt 复现方案。

---

## 一、触发条件（严格判断）

**走路径 B 必须同时满足**：

1. 用户**没有**提供素材路径或长文本
2. 用户**明示**要做研究，关键词列表：
   - "试试这个主题 X"
   - "用 STORM 研究 X"
   - "研究这个话题 X"
   - "/storm X"
   - "research mode: X"
   - "从这个主题写一篇 X"
   - "我没有素材，帮我研究 X"
   - "深入研究 X"（带"深入研究"必触发）
3. 输入是 1 个主题（短语，通常 ≤ 30 字）

**不触发的情况**（永远走路径 A）：
- 用户给了素材路径或长文本（即使顺嘴说"研究"）
- 用户说"基于这些素材研究 X"（这是路径 A 的多素材整合）
- 用户只说"看看 X"、"分析 X"——不够明示
- 用户说"我有素材，但想再补一些研究"——这是混合模式（路径 A 主、可选触发路径 B 补充，但本 skill 当前**只支持纯路径 A 或纯路径 B**，混合模式让用户先跑路径 B，把 briefing 作为额外素材合并后走路径 A）

---

## 二、严格 4 步独立 prompt（不要合并、不要跳）

**4 个 prompt 必须按顺序、独立完整跑完**。每个 prompt 输出完整后，才进下一个。**绝不合并、绝不跳步、绝不改写 prompt 原文**。

### Prompt 1 / 4 — 五角度扫描

把第一行的 `[YOUR TOPIC]` 换成用户的话题（中文话题直接保留中文，比如 `loop 工程`）：

```text
I need to research [YOUR TOPIC].
Simulate 5 different expert perspectives on this topic:
1. THE PRACTITIONER: works with this daily.
What do they know that academics miss?
What practical realities are usually ignored?
2. THE ACADEMIC: has studied this for years.
What does the peer reviewed evidence actually say?
Where does the evidence contradict popular belief?
3. THE SKEPTIC: thinks the mainstream view is wrong.
What is the strongest counterargument?
What evidence do proponents conveniently ignore?
4. THE ECONOMIST: follows the money.
Who profits from the current narrative?
What financial incentives shape the research?
5. THE HISTORIAN: has seen similar patterns before.
What historical parallels exist?
What can we learn from how those played out?
For each perspective give me:
- Their core position in 2 sentences
- The strongest evidence supporting their view
- The one thing they would tell me that no other perspective would
```

**设计点拆解**：

- 5 个角色相互正交（实操 vs 学术 vs 反对 vs 利益 vs 历史）
- 每个角色都得给 3 件事：核心观点（2 句）、最强证据、**其他角色不会说的一句话**
- 最后那句"独占视角"强制 5 种不重叠的独占信息累加 → **10% 覆盖面增长的来源**

**等 5 个角色完整输出后，才进 Prompt 2。**

---

### Prompt 2 / 4 — 矛盾图

5 个角色完整输出后立刻接：

```text
Based on the 5 perspectives above, map the contradictions:
1. Where do two or more perspectives directly contradict
each other? List each conflict with the specific claims
that clash.
2. Which perspective has the strongest evidence?
Which has the weakest? Why?
3. What is the one question that, if answered, would
resolve the biggest contradiction?
4. What does EVERY perspective agree on?
(This is likely true. Even opponents confirm it.)
5. What topic did NONE of the perspectives address?
(This is the blind spot in the whole field.
Often the most valuable finding.)
```

**设计点拆解**：

- 5 个问题各自做一件事：找直接冲突 / 证据强弱排序 / 关键问题 / 共识区（很可能真）/ 共同盲区（最值钱）
- 强制 AI 不停在"软化共识"上，而是 structurally 把冲突点摆出来 → **25% Organization 提升的来源**
- 共同盲区是这一步的金子：@heynavtoor 原话「If nobody addressed a topic, you just found the gap in the entire field」

---

### Prompt 3 / 4 — 综合 briefing

矛盾图完整输出后接。**记得把第 4 项的 `[YOUR ROLE]` 换成用户的具体角色**（默认填"内容创作者"，如果用户在对话里说过自己的角色就填那个，比如"产品经理"、"独立开发者"、"投资人"）：

```text
Synthesize everything from the 5 perspectives and the
contradiction map into a research briefing:
1. THE ONE PARAGRAPH SUMMARY: explain this topic as if
briefing a CEO who has 60 seconds and needs nuance,
not just the headline.
2. THE 5 KEY FINDINGS: most important things I now know,
ranked by reliability. For each, note which perspectives
support it and which challenge it.
3. THE HIDDEN CONNECTION: one non obvious link between
findings that only shows up when you look at all 5
perspectives together.
4. THE ACTIONABLE INSIGHT: based on all the evidence,
what should someone in [YOUR ROLE] actually DO
differently? Be specific.
5. THE FRONTIER QUESTION: the one question that, if
answered, would change everything about how we
understand this topic.
```

**设计点拆解**：

- "60 秒给 CEO 汇报"格式逼出精确度（要 nuance，不要 headline）
- 5 关键发现 + 哪些角色支持 / 挑战 → 直接给后续 dbs 五维诊断的素材
- 隐藏连接 → 单 prompt 永远拿不到的洞察，往往是文章最有价值的"非显然"金句
- `[YOUR ROLE]` 替换让"研究 → 行动"成型，不只是知识堆

---

### Prompt 4 / 4 — 同行评审（**绝对不能省**）

综合 briefing 完整输出后接：

```text
Now peer review your own research briefing:
1. CONFIDENCE SCORES: rate each of the 5 key findings
on a 1 to 10 scale for reliability. Explain each score.
2. WEAKEST LINK: which claim are you least confident in?
What specific info would you need to verify it?
3. BIAS CHECK: which perspective might be overrepresented
in your synthesis? Did one voice dominate?
4. MISSING PERSPECTIVE: is there a 6th angle I should
have included that would change the conclusions?
5. OVERALL GRADE: if a Stanford professor reviewed this
briefing, what grade would they give and why?
What would they tell me to fix?
```

**设计点拆解**：

- 同行评审强制 AI 反向审视自己 → 绕开 Self-preferential Bias（Dynamic Workflows 文章列的失效模式之一）
- 1-10 信心评分 → 避免"所有发现都看起来一样可信"的幻觉
- 偏见检查 / 缺失视角 → 补 Stanford 自己承认的 STORM 弱点（source bias + fact misassociation）
- Stanford 教授视角打分 → 用最严格的视角自检

**这一步是 STORM 与单纯 5 角度提问的根本差别**。省了 = 退化成提示词技巧。

---

## 二·5、Step 0.5.5：强制 Fact-Check Pass（**绝对不能省**）

> **来源**：2026-06-20 用户反馈——批评 AI 指出 v1/v2 输出里**多处虚构具体引用**（DeepMind 2024 paper 应为 2020、OpenAI System Card 没有 long-horizon loop 强制 checkpoint 要求等）。LLM 模拟跑 STORM 天然会编出"看起来精确但虚构"的具体引用。这一步是修复机制。

### 为什么必须 fact-check

Prompt 1 的 "strongest evidence supporting their view" 字段，**强制 LLM 给出具体证据**。LLM 没有外部数据源时，会用内部知识 + 填补创造混合生成：
- 论文年份："2024" / "2025"（往往跟实际错 1-3 年）
- 报告名称："某公司某年系统卡"（往往合并多个真实报告 + 虚构细节）
- 百分比："90% 工程量"、"70% issue 类型"（无统计支撑）
- Issue 数据："GitHub issue tracker 70% 都是 X"（没真去 GitHub 数）

**这些虚构如果带进 briefing 进入 3 平台公开发布，等于散布虚假引用，是比 AI 味严重得多的诚信问题**。

### Step 0.5.5 操作流程

**Prompt 4 同行评审完成后，立刻进 Step 0.5.5，不要直接跳 Step 1**。

#### 第 1 步：扫描所有具体引用

在 Prompt 1（5 视角）+ Prompt 3（briefing）的输出里，**逐句标记**以下类型的内容：

- **具体年份**："2024 paper"、"2025 system card"、"2023 ICLR"
- **具体报告/论文/产品名**："DeepMind specification gaming"、"OpenAI System Card"、"Anthropic Dynamic Workflows"
- **具体百分比**："90%"、"5-30%"、"70% issue"
- **具体数字**："40-60 小时"、"5-10x cost"
- **具体人物 + 立场**："trq212 在 X 文章里说...""xxx 论文证明..."
- **具体平台 issue 描述**："LangChain issue tracker 大量..."

每个标记的引用，进入第 2 步。

#### 第 2 步：WebSearch 逐条验证

对每一个标记的引用，跑 WebSearch（或 WebFetch 找原始来源）：

| 验证结果 | 处理方式 |
|---------|---------|
| ✅ 完全匹配（年份对、出处对、原文有这个意思） | 保留，标 `[已验证 URL]` |
| ⚠️ 部分匹配（出处存在但年份错 / 原文意思有出入） | **修正具体细节**（改对年份 / 改对出处），然后标 `[已修正 URL]` |
| ❌ 找不到 / 与原文意思矛盾 | **删除具体引用**，改用软化措辞：「有研究指出」「业界讨论中」「据观察」「Anthropic 团队透露」等。**绝不保留虚构的具体年份/出处** |

#### 第 3 步：briefing 修订

修订后的 briefing 里，**每一个具体引用都必须**：
- 标 ✅ + URL（已验证）
- 或标 ⚠️ + URL（已修正）
- 或软化成"业界讨论"、"有研究指出"（不能再带具体年份/出处）

### 没有 WebSearch 工具的情况

如果当前环境**没有 WebSearch 工具**（比如离线、配置缺失），路径 B **有两个合法选择**：

1. **直接退出路径 B**：告诉用户"当前环境无 WebSearch，路径 B 跑不出 grounded briefing。建议给我素材路径走路径 A，或在有 WebSearch 的环境里重跑"
2. **全篇软化措辞**：跑 STORM 4 prompt，但**强制所有具体引用都改成"业界讨论中"、"有观点认为"**，**不许出现任何具体年份/出处/百分比**。briefing 在创作说明里明确标注"无 grounding 环境产出，全部为软化措辞"

**不许装作有 grounded 引用**——这是诚信问题，不是 quality 问题。

### Step 0.5.5 完成后的最终 briefing 格式

```
## 5 角度扫描（已 fact-check）

### Practitioner
- Core position: {内容}
- Strongest evidence: {内容} [✅ 已验证 / ⚠️ 已修正 / 软化措辞]
- One thing only they would say: {内容}

...（其他角色同上）

## 矛盾图（已 fact-check）
...

## 综合 briefing（已 fact-check）

### 5 KEY FINDINGS（按可靠性 + grounding 双排序）
| 排名 | Finding | 可靠性 | grounding 状态 | 来源 |
|------|---------|--------|---------------|------|
| 1 | {finding} | 9/10 | ✅ 已验证 | [URL] |
| 2 | {finding} | 7/10 | ⚠️ 已修正 | [URL] |
| 3 | {finding} | 6/10 | 软化措辞 | 无具体来源 |
...
```

### Gotchas（专门针对路径 B 虚构引用）

- **LLM 模拟跑 STORM 100% 会编引用**。这不是 bug，是 LLM 在没有外部数据源时填 "strongest evidence" 字段的必然行为。**Step 0.5.5 是修复机制，必须做**
- **批评 AI / fact-checker 会扒出来**。2026-06-20 的事件就是证据——批评 AI 指出 v1/v2 输出里 7 大类虚构引用，全部成立
- **诚实声明不等于免责**：之前 SKILL.md 写了"⚠️ 本 briefing 是 LLM 模拟产物"——这是诚实声明，但**没阻止具体引用被当事实读**。读者只会看正文，不会回头看声明
- **软化措辞不丢内容价值**：「有研究指出 reward signal 漏洞会被 loop 放大」跟「DeepMind 2024 paper 证明 reward signal 漏洞会被 loop 放大」**信息量基本一样**，但前者没诚信问题
- **优先级**：fact-check 比"风格优雅"重要，比"字数控制"重要，**只比"完整原文贴 prompt"低一个等级**

---

## 二·6、Step 0.5.6：Frame Switch（**进 Step 1 前的最后一步，必做**）

> **来源**：2026-06-20 用户反馈——v3 输出全部跑偏到 STORM 元过程，整篇内容讲"我用 STORM 研究 loop 工程""我编引用翻车"，而不是 loop 工程本身。这是 framing drift，比编引用更严重。

### 为什么必须做 Frame Switch

STORM 4 prompt + fact-check 这个过程**太有戏剧性**——5 视角扫描、矛盾、综合、自评、翻车、修正——AI 在跑完之后**沉浸在"我刚做了什么"的视角里**。

进 Step 1 时如果不切换 frame，产出会变成：
- ❌ 标题：「我用 STORM 6 视角研究 X，浮出一个被忽略的双约束」
- ❌ 正文：花大段讲 STORM 流程、引用我修正了什么
- ❌ 卡片图：1/3 在讲 fact-check 翻车经验

**这些都是用户没有要的元内容**。用户问的是 **subject**（loop 工程），不是 **frame**（STORM）。

### Frame Switch 操作

进入 Step 1 之前，**强制做一次心理切换**：

**之前 frame**（错的）：
> 我用 STORM 6 视角 + WebSearch fact-check 跑了一份关于 X 的研究 briefing，现在要把这个过程写成文章。

**正确 frame**：
> 我现在有一份关于 X 的素材（briefing）。这份素材怎么来的不重要，重要的是它告诉了我 X 的什么。我要根据这份素材，给用户产出关于 **X 本身**的 3 平台内容。

具体动作：
1. **忘掉 STORM 流程**：跑 STORM 是历史，现在你的输入就是 briefing
2. **把 briefing 当路径 A 的"用户素材"处理**：像用户给你了一份 Obsidian 笔记一样，从素材出发，不要回头看"这份素材是怎么来的"
3. **STORM 来源最多在末尾一句话标注**（"本文综合自 ReAct 论文 + Anthropic Dynamic Workflows + DeepMind specification gaming 等公开材料，用 Stanford STORM 多视角方法整理"），**不许展开**

### 进 Step 1 前的最后自检 — 两个测试题

#### 测试 1：删 STORM 测试

把 3 平台输出里所有提到 STORM / fact-check / "我用 X 方法跑了一遍" 的段落**删掉**，剩下的内容：
- ✅ 还能成立、还是关于 [主题] 的 → 通过
- ❌ 内容散架 / 失去主线 → **跑偏了**，回去重写

#### 测试 2：读者测试

一个**完全不知道 STORM 是什么**的读者读完，他能学到关于 [主题] 的什么？
- ✅ 能清晰说出 [主题] 的 2-3 个核心点 → 通过
- ❌ 答不上来，只记得"作者用了某个研究方法" → **跑偏了**

### 标题守护规则

**所有 3 平台标题必须直接命中用户输入的主题**：

| 用户输入主题 | ✅ 正确标题 | ❌ 错误标题（framing drift） |
|------------|------------|--------------------------|
| loop 工程 | 「Loop 工程难在哪？早停和对齐是两本不同的书」 | 「我用 STORM 6 视角研究 loop 工程，浮出一个被忽略的双约束」 |
| RAG | 「RAG 的真正瓶颈不在 retrieval」 | 「STORM 方法告诉我 RAG 缺什么」 |
| MCP | 「MCP 解决了 LLM 的什么具体问题」 | 「我用 STORM 跑完 MCP，发现 5 个角度」 |

**规则**：标题里**不许出现** STORM、fact-check、"我用 XX 方法研究" 这种字样。

### 篇幅守护规则

| 内容类型 | 建议占比 |
|---------|---------|
| **主题本身的内容**（用户想看的） | ≥ 80% |
| **来源说明 / 方法说明**（STORM 等） | ≤ 15%，最好集中在 1 段或文末 |
| **元过程 / fact-check 经验** | **0%**——这是另一篇文章，不要混进来 |

### 例外情况：什么时候允许写 STORM 元过程

**只有一种情况**：用户的输入**主题本身就是研究方法 / fact-check / SKILL 设计**——比如用户说"试试这个主题：STORM 方法"或"研究 fact-check 的最佳实践"。这时候 STORM 才是 subject。

判断标准：**用户输入字符串中的主题词是不是 "STORM" 或 "fact-check" 或类似的研究方法相关词**？
- 是 → STORM 元过程可以是主题
- 否 → STORM 必须只是 footnote

### Gotchas

- **AI 跑完 STORM 后天然会想写 STORM**——这是 cognitive bias，不是设计 bug。SKILL.md 的 framing drift 守护就是修这个 bias
- **诚实声明 ≠ 主题漂移**：可以在文末标"本文综合自 STORM 多视角方法"，但**不能把 STORM 流程当主题**
- **fact-check 翻车的戏剧性是 trap**：跑完 fact-check 发现自己之前编了引用，这个"翻车瞬间"会让 AI 想专门写一篇"我怎么翻车了"。**这是另一篇文章**，跟用户问的主题无关，不要混进当前任务
- **优先级**：framing drift 守护 > fact-check（编引用是细节失败，framing drift 是方向失败）

---

## 二·7、Step 0.5.7：Social Signal Collection（**抓 What People Are Saying**）

> **来源**：2026-06-20 用户反馈——STORM 6 视角是 LLM 模拟的"理论视角"，没有当下事件、没有真实人物、没有实时讨论。loop 工程 2026-06 月爆火源头是 Boris Cherny (Claude Code 创始人) 的"I don't prompt Claude anymore. I have loops running that prompt Claude"宣言 + Anthropic 内部 talk——这种当下事件 LLM 模拟拿不到，必须用 opencli 抓。

### 为什么必须做 Social Signal Collection

STORM 6 视角的本质是 LLM 模拟的"理论角色"——Practitioner / Academic 等都是想象出来的角色。这导致：

- ❌ **没有具体真实人物**（不知道 Boris Cherny / @omarsar0 / @bcherny 这些当下的 thought leaders）
- ❌ **没有当下事件**（不知道某个推文 6 月发的、刷屏了多少 likes / views）
- ❌ **没有正在发生的讨论**（不知道社区里在吵 verifier / harness / state 这些具体技术分歧）
- ❌ **没有具体生产案例**（不知道有人在生产里跑几百个 agent、几千个 routine）

**产出会变成"AI 教科书分析"**：讲早停、讲 alignment、讲失效模式——都对，但读完没人会转发。因为缺**当下感**。

### Step 0.5.7 操作流程

**Step 0.5.6 frame switch 完成后、进 Step 1 之前，必做 Social Signal Collection。**

#### ⚠️ 第 1 步的失败模式（2026-06-21 用户反馈，已沉淀）

**错误做法**：
1. 找一条 viral 推文（如 Boris Cherny / Satya Nadella 的）
2. 用 `opencli twitter thread <id>` 抓**回复区**
3. 在几十条回复里挑"看起来有具体观点"的句子

**为什么错**：
- 回复区 80% 是 spam reply / "great post" / 营销刷屏 / 低 reach 个体观点
- "几十条回复里看起来有金句的" ≠ "社区共识"，而是 **一个低 reach 个体的观点**
- 真正的"社区在说什么" = **X 上所有人讨论这个 topic 的高互动原创推文**，不是某条 viral 帖子的回复

**正确做法**：围绕 **topic 关键词** 在 X 全网搜，不在某条推文的**回复区**搜。

#### 第 1 步：列出 topic 关键词（围绕主题，不围绕单个推文）

主题（比如 `用 AI 巩固个人护城河`）→ 拆出 5-10 个 topic 关键词：

中文 + 英文都要列。例（个人护城河主题）：
- "AI 护城河 个人"
- "personal moat AI era"
- "AI 时代 个人能力"
- "human moat AI"
- "AI collaboration personal"
- "AI as teacher learn"
- "critical thinking AI"
- "learning by output AI"

**子主题各自列关键词**，不要混在一起搜。

#### 第 2 步：围绕 topic 搜 X 全网（不抓回复区）

```bash
# 围绕 topic 全网搜——这是正确路径
opencli twitter search "topic 关键词" -f md | head -30

# 默认按相关度 + 时间排序，结果包含 likes / views 字段
# 不要再用 `opencli twitter thread <id>` 抓回复区
```

**特殊情况可用 thread**：
- 主题热度源头是**某条具体 viral 推文**（如 Boris 那句"deleted my IDE"），可以抓主推文 + **作者后续的 self-reply**
- 但**不抓陌生人的 reply**——chosen replies 是策展，回复区不是

**这一步是抓血肉。**

#### 第 3 步：在抓到的真实推文里挑"金子级"声音

**【强制准入门槛 — 2026-06-20 用户反馈后加】**

每条候选引用必须**同时满足**：
- ✅ **作者 followers ≥ 3000**（用 `opencli twitter profile <user> -f yaml | grep followers` 查）
- ✅ **该条推文 views ≥ 5000**（thread 输出表格里有 `views` 列）

**一个不达标就剔除**，不要折中。低 reach 推文 = 没经过群体验证 = 可能是个体偏见 / AI 自动回复 / 营销刷屏。

**批量验证脚本**：

```bash
for user in user1 user2 user3; do
  followers=$(opencli twitter profile $user -f yaml 2>&1 | grep "followers:" | awk '{print $2}')
  if [ "$followers" -ge 3000 ] 2>/dev/null; then
    echo "✅ @$user: $followers"
  else
    echo "❌ @$user: $followers (< 3k, 剔除)"
  fi
done
```

#### 第 3.5 步：内容质量二次过滤（在准入门槛之后）

通过准入门槛后，再筛选 5-10 条具有以下特征的：
- ✅ **具体观点**（不是 "great post!" 这种 spam reply）
- ✅ **专业身份**（profile 有 Founder / CTO / 在某公司做 X）
- ✅ **可引用的金句**（有自己的洞察、有反差、有数字）
- ✅ **有 URL**（每条都能 link 回去验证）

❌ 排除：纯 emoji reply / "saved!" / "this is great" / promotion spam

**两个常见失败模式**：
1. **把 thread 回复区"看起来精确的金句"当社区共识** → 错。回复区大多是低 reach 个体观点，**不是社区在说什么，是一个人在说什么**
2. **把 bio 听起来权威的当背书**（如 "30 年公司治理者"）→ 错。bio 自己写的，**看 reach 数据，不看自我介绍**

**特例**：
- 作者是公认领域权威（如 [@bcherny](https://x.com/bcherny) / [@AndrewYNg](https://x.com/AndrewYNg) / [@satyanadella](https://x.com/satyanadella) 等 KOL）但单条 view 偏低 → **找他另一条 view ≥ 5k 的**，不要将就
- 观察非常独特但作者 reach 低 → 可作为"待二次验证的观察"放参考，**不作为正文核心引用**

**优先级排序**（写文章时）：
1. 顶级权威发的 viral 推文（如 Boris Cherny / Andrew Ng / Satya Nadella）
2. 中等 KOL 的高互动推文（粉丝 1w+，单条 likes 100+）
3. 准入门槛达标的具体观点
4. （以下不直接引用）低 reach 个体观点

#### 第 4 步：把真实声音作为正文素材

**核心调整**：真实社区声音的权重 **高于** STORM 模拟视角。

| 内容元素 | 来源优先级 |
|---------|----------|
| 文章开头钩子 | **真实当下事件**（Boris 的具体宣言 + URL）> STORM 模拟 |
| 主体核心观点 | 真实社区争论的具体痛点（verifier / harness / state）> STORM 综合 briefing |
| 引用句 | **真实人物原话 + @handle + URL** > LLM 模拟的"Practitioner 说" |
| 数据 / 案例 | **真实推文的 likes / views / 转发** > LLM 编造的百分比 |

### Step 0.5.7 完成后的最终素材包

进 Step 1 时，你的"素材"应该是 **两层结构**：

**第一层（血肉，主要来源）**：opencli 抓到的真实推文 + 关键人物原话 + URL
**第二层（框架，辅助结构）**：STORM 6 视角 briefing（已 fact-check）

写正文时按这个权重：
- 80% 引用真实人物 + 真实推文 + 真实事件
- 20% 用 STORM 框架做结构性组织（比如分早停 / alignment / verifier 三个维度）

### 真实社区声音的引用格式

```markdown
[@bcherny (Boris Cherny, Claude Code 创始人)](https://x.com/bcherny) 6 月在 Anthropic 内部 talk 中那句话刷屏了：

> "I don't prompt Claude anymore. I have loops running that prompt Claude... My job is to write loops."

社区里 [@tyrtyre201](https://x.com/tyrtyre201/status/...) 接了一句更狠的：

> "Stop prompting. Start engineering loops. Most people still haven't gotten this memo."

而 [@Primee32](https://x.com/Primee32/status/2068243907679293576) 直接点出了被忽略的关键：

> "the verifier is the most important part and nobody talks about it. a model grading its own work passes almost everything."
```

**注意**：
- 每个引用都附 `@handle + URL`
- 引用要逐字（不要改 punctuation / 不要"美化"）
- 中英文混合时，外文 quote 保持原文 + 可选附中文翻译

### 没有 opencli / WebSearch 工具的情况

如果当前环境**没有 opencli 也没有 WebSearch**（极少情况），路径 B 必须**诚实声明**：

```
⚠️ 当前环境无法抓真实社区声音（opencli / WebSearch 不可用）。
本文产出只有 STORM 6 视角模拟框架，没有当下事件 / 真实人物 / 实时讨论。
内容会显得抽象、缺当下感。建议在有 opencli 的环境重跑。
```

**不许装作有当下感**——这是诚信问题。

### Gotchas

- **STORM 没有当下感**——它是模型内部知识的推演。当下事件必须从真实社区抓
- **opencli 抓到的真实声音权重高于 STORM 模拟**——前者带名字、URL、likes 数，后者是 LLM 想象
- **关键人物 = 当下事件的源头**：不挑就是把所有人都模糊掉。loop 工程是 Boris；RAG 可能是 Yi Tay；MCP 可能是 Anthropic 官方账号——**每个热门主题都有具体的人在推**
- **viral thread 的回复区是金矿**：一条几百 likes 的推文，回复区往往有 10-20 条具体观点。这些是 STORM 拿不到的
- **不要全用英文 quote 让中文读者读不懂**：核心金句保留英文原文 + 附中文翻译 / 转述
- **优先级**：Social Signal > Fact-Check > Framing Drift 守护 > 其他自检。**当下感是 AI 文章的命门**，没当下感再正确也没人读

---

## 三、4 个 prompt 跑完后：briefing 怎么接 Step 1

把 **Prompt 3 的综合 briefing + Prompt 4 的自评**，作为路径 A Step 1 的"素材"传下去。

具体接口：

| 路径 A Step 1 字段 | 路径 B 中对应的 briefing 内容 |
|--------------------|--------------------------|
| **核心观点** | Prompt 3 的"ONE PARAGRAPH SUMMARY" |
| **第一手观察** | 路径 B **天生缺这个**——briefing 是 LLM 模拟，不是真实经历。下游必须知道这点（影响原型选择，详见下方 Gotchas） |
| **数据 / 案例 / 金句** | Prompt 3 的"5 KEY FINDINGS" + "HIDDEN CONNECTION"，附带 Prompt 4 的 confidence score |
| **HKR 评估** | H：用 Prompt 3 的"FRONTIER QUESTION"判断有无悬念；K：用 5 KEY FINDINGS 判断信息量；R：用 ACTIONABLE INSIGHT 判断戳痛点 |

**后续 Step 2-5 完全按路径 A 跑**，零额外步骤。

---

## 四、Gotchas（持续累积）

- **绝不合并 prompt**：4 个 prompt 是 STORM 的核心设计。合并会变成"高级 5 角度提问"，丢掉矛盾图 / 综合 / 同行评审 3 步的价值
- **绝不省略 Prompt 4**：自评步骤是 STORM 与单纯 5 角度提问的根本差别。Stanford 自己承认 STORM 弱点（source bias + fact misassociation）就靠这步补
- **`[YOUR TOPIC]` 和 `[YOUR ROLE]` 必须替换**：忘了替换，AI 会按字面字符串理解，输出垃圾
- **prompt 用英文原文，不翻译**：4 个 prompt 是 Stanford 原版，翻译会丢精度。即使中文话题，prompt 框架也用英文，话题用中文嵌进 `[YOUR TOPIC]` 即可
- **路径 A 优先**：如果用户给了素材路径或长文本，**永远走路径 A**，即使他顺嘴说了"研究"
- **briefing 缺第一手观察 → 影响原型选择**：路径 B 的 briefing 是 LLM 模拟，**天生没有第一手观察 / 真实经历 / 体感细节**。这意味着：
  - 调查实验型、产品体验型这两种原型**几乎不适合**路径 B（它们需要"我亲自下场"的痕迹）
  - 现象解读型、工具分享型、方法论分享型**可适合**路径 B
  - Step 3 选原型时，**默认在这 3 个里挑**
- **briefing 是 LLM 模拟的，要在文章中诚实表态**：3 平台输出时，不能写"我观察到 / 我经历过"这种话——briefing 没有真实经历。改用"Stanford 研究指出 / 5 个视角里 / 综合 5 个专家视角看"等表达，**诚实标注研究方法的来源**
- **触发关键词不严格的话不触发**：用户只说"看看 X"、"分析 X"——不够明示。明示触发的关键词必须有"研究" / "STORM" / "话题" / "没素材" / "深入研究"之一
- **不要在 Step 0.5 中夹带额外指令**：4 个 prompt 严格按原文跑，不要在 prompt 之间加"补充说明"。每个 prompt 独立运行，AI 内部上下文已经够用

---

## 五、Step 0.5 完成后向用户报告的格式

跑完 4 个 prompt 后，进 Step 1 之前，**用这个格式简短报告给用户**：

```
## STORM 研究完成

主题：{TOPIC}
角色：{ROLE}

**5 角度扫描完成**：Practitioner / Academic / Skeptic / Economist / Historian 各 1 份独占视角
**矛盾图**：发现 N 个直接冲突 + N 个共识 + N 个共同盲区
**综合 briefing**：5 个排序后的关键发现 + 1 个隐藏连接 + 1 个可执行洞察 + 1 个前沿问题
**同行评审**：平均信心分 X.X/10，最弱论点是 {简述}，缺失视角是 {简述}

⚠️ 提醒：本 briefing 是 LLM 模拟 5 视角的研究产物，**不是基于真实第一手观察**。
进入 Step 1-5 时，文章原型默认在「现象解读 / 工具分享 / 方法论分享」3 种里选。
3 平台输出时诚实标注：「这次内容是基于 STORM 5 视角研究」，**不假装自己亲身经历过**。

---

现在进入 Step 1：理解素材（briefing 作为素材）...
```

这一步既透明又预防"假装亲身经历"的失效模式。
