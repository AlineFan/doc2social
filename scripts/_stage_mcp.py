#!/usr/bin/env python3
# 把 MCP 文章渲染所需的一切 stage 成 ASCII 名，避开 macOS 中文文件名规范化坑。
import os, shutil

DIR = "/Users/doushun/本地文稿/Obsidian Vault/【1】WAY2AI/【1.5】output"
N = "很多人把 MCP 用重了：你以为你在增强 Agent，其实你在塞爆上下文"
note = os.path.join(DIR, N + ".md")
ILLUS = os.path.join(DIR, N + "-illustrations")
PROJ = "/Users/doushun/Desktop/workspace/proj04-obsidian-publisher"
STAGE = os.path.join(PROJ, "output", "mcp-render")
os.makedirs(STAGE, exist_ok=True)

# 1) 读原文 + 6 张配图按锚点插入（ASCII 引用名）
text = open(note, encoding="utf-8").read()
lines = text.split("\n")
inserts = [
    ("**你以为你在增强 agent，实际上你可能只是在让它更笨、更容易分心。**", 1),
    ("**AI 和外部系统之间的一套通信标准。**", 2),
    ("**你挂 3 个 MCP server，和你挂 80 个 MCP server，会话开局的重量就是不一样。**", 3),
    ("> **调用之后，服务到底会往模型脑子里塞回多少东西。**", 4),
    ("**不要一上来就把全集扔给模型。**", 5),
    ("> **模型能不能在最小噪声下，拿到刚刚好的外部能力。**", 6),
]
anchor = {a: n for a, n in inserts}
done = {n: False for _, n in inserts}
out = []
for line in lines:
    out.append(line)
    k = line.strip()
    if k in anchor and not done[anchor[k]]:
        n = anchor[k]
        out.append("")
        out.append("![[perbrand-0%d.png]]" % n)
        done[n] = True
staged_md = os.path.join(STAGE, "mcp-staged.md")
open(staged_md, "w", encoding="utf-8").write("\n".join(out))
print("锚点命中:", {n: done[n] for n in sorted(done)})
miss = [n for n, ok in done.items() if not ok]
print("未命中:", miss if miss else "无")

# 2) 6 张配图拷成 ASCII 名（与 staged HTML 同目录，inline-images 相对路径直接命中）
for i in range(1, 7):
    s = os.path.join(ILLUS, "%s-perbrand-0%d.png" % (N, i))
    d = os.path.join(STAGE, "perbrand-0%d.png" % i)
    shutil.copy2(s, d)
imgs = sorted(f for f in os.listdir(STAGE) if f.endswith(".png"))
print("配图:", imgs)

# 3) 上一篇绿色科技风产出拷成 ASCII 名，给渲染 subagent 当「定制参照」
ref = os.path.join(PROJ, "output", "Skill 装太多，Agent 反而变笨-绿色科技风.html")
refdst = os.path.join(STAGE, "ref-green.html")
if os.path.isfile(ref):
    shutil.copy2(ref, refdst)
    print("参照(ref-green.html):", os.path.getsize(refdst), "bytes")
else:
    print("⚠️ 找不到参照:", ref)

print("STAGE:", STAGE)
