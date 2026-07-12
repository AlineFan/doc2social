#!/usr/bin/env python3
"""
gzh-layout-cloner 提取侧的确定性插件（LLM 全包流程的 prep / validate / render 三步）。
组件归纳由 subagent 读 prep 产物 + SKILL.md「提取契约」完成（正则枚举式提取已退役）。

  prep <url> <名>   抓 js_content → 样式清单 + 清洗结构视图（喂 LLM 归纳）
  validate <名>     机器校验 templates/<名>.json（schema / 必备件 / box-sizing）
  render <名>       从 <名>.json 出可视化预览 HTML
"""

import json
import os
import re
import sys
import subprocess
from collections import OrderedDict


# ── 1. 抓取 & 提取 js_content ──────────────────────

def fetch_html(source: str) -> str:
    """从 URL 或本地文件读取 HTML"""
    if source.startswith("http"):
        result = subprocess.run(
            ["curl", "-sL", "-A",
             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
             source],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    with open(source, "r", encoding="utf-8") as f:
        return f.read()


def extract_js_content(html: str) -> str:
    """提取 id='js_content' 的 div 内容"""
    marker = 'id="js_content"'
    start = html.find(marker)
    if start == -1:
        raise ValueError("找不到 js_content 区域")
    # 回退到 <div
    tag_start = html.rfind("<", 0, start)
    # 用计数器找配对的 </div>
    depth = 0
    i = tag_start
    while i < len(html):
        if html[i:i+4] == "<div":
            depth += 1
        elif html[i:i+6] == "</div>":
            depth -= 1
            if depth == 0:
                return html[tag_start:html.index(">", i) + 1]
        i += 1
    raise ValueError("js_content 区域解析失败")


# ── 2. 样式解析工具 ──────────────────────────────

def unescape_html(s: str) -> str:
    """还原 HTML 实体"""
    import html as html_mod
    return html_mod.unescape(s)


def parse_style(style_str: str) -> dict:
    """把 inline style 字符串解析成 dict"""
    if not style_str:
        return {}
    style_str = unescape_html(style_str)
    result = OrderedDict()
    for part in style_str.split(";"):
        part = part.strip()
        if ":" in part:
            key, _, val = part.partition(":")
            result[key.strip()] = val.strip()
    return result


def style_to_str(d: dict) -> str:
    return ";".join(f"{k}:{v}" for k, v in d.items())


def clean_text(html_fragment: str) -> str:
    """去除 <span leaf=""> 等标签，只保留纯文本"""
    return re.sub(r"<[^>]+>", "", html_fragment).strip()


# ── 3. 骨架渲染 & 通用预览 ────────────────────────



def _fill_slot_samples(html: str, slots: dict) -> str:
    """把骨架里的 {{SLOT}} 换成中性占位（不用 example 的参考内容，避免样板泄漏进预览）"""
    GENERIC = {
        "CATEGORY": "分类 · 示例", "DATE": "2026.06", "COUNTER_HOOK": "反话钩子（划掉）",
        "TITLE_LINE1": "标题首行", "TITLE_LINE2": "标题次行", "SUBTITLE": "副标题 / 核心一句话",
        "BRAND": "品牌名", "COUNT": "N", "NUM": "01", "TITLE": "分节标题", "ENGLISH": "SECTION",
        "INDEX": "01", "HEADING": "小标题示例", "TAG": "标签", "NN": "01",
    }
    def repl(m):
        name = m.group(1)
        sd = slots.get(name, {})
        if isinstance(sd, dict) and sd.get("default"):
            return sd["default"]
        return GENERIC.get(name, "示例")
    return re.sub(r'\{\{(\w+)\}\}', repl, html)


def _render_skeleton_components(components: dict, skeleton_dir: str) -> list:
    """把带 skeleton_ref 的复杂组件（封面卡 / 横滚目录 / 底部三连等）渲染进组件清单预览。
    读骨架片段、用中性占位填 {{槽位}}。part_heading / heading_index_pill 已由上面的代码渲染，跳过避免重复。"""
    SKIP = {"part_heading", "heading_index_pill"}
    backed = [(k, v) for k, v in components.items()
              if isinstance(v, dict) and isinstance(v.get("skeleton_ref"), str)
              and "#" in v["skeleton_ref"] and k not in SKIP]
    if not backed:
        return []
    skfile = backed[0][1]["skeleton_ref"].split("#", 1)[0]
    path = os.path.join(skeleton_dir, skfile)
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    # 按 "<!-- ===== <anchor> ... ===== -->" 把骨架切成各组件片段
    chunks = re.split(r'<!--\s*=+\s*(\w+)[^>]*?=+\s*-->', text)
    sections = {}
    seq = iter(chunks[1:])
    for name, body in zip(seq, seq):
        sections[name] = body
    out = []
    for key, comp in backed:
        anchor = comp["skeleton_ref"].split("#", 1)[1]
        body = sections.get(anchor)
        if not body:
            continue
        slots = comp.get("slots", {})
        # repeat 的 item 模板藏在注释里（item / active / default）
        items = {}
        for m in re.finditer(r'<!--\s*(item|active|default)\s*:\s*(.+?)\s*-->', body, re.DOTALL):
            items.setdefault(m.group(1), m.group(2).strip())
        # 主体 = 去掉所有注释
        main = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL).strip()
        # 填重复容器槽
        if "{{TAG_PILLS}}" in main and "item" in items:
            main = main.replace("{{TAG_PILLS}}", _fill_slot_samples(items["item"], slots) * 2)
        if "{{TOC_CARDS}}" in main:
            cards = "".join(_fill_slot_samples(items[k], slots) for k in ("active", "default") if k in items)
            main = main.replace("{{TOC_CARDS}}", cards)
        # 填标量槽
        main = _fill_slot_samples(main, slots)
        label = comp.get("description", key).split("（")[0].strip() or key
        out.append(f'<p class="comp-label">★ {label}</p>')
        out.append(main)
    return out




def _flatten_style(style: dict) -> dict:
    """扁平或嵌套 style → 一个扁平 dict。嵌套时合并所有子层的字符串属性（浅层优先）。
    这样『section>p>strong』这种带 wrapper 的标题也能拿到 font-size 等关键样式来渲染。"""
    flat = {}
    if not isinstance(style, dict):
        return flat
    for k, v in style.items():
        if isinstance(v, str):
            flat[k] = v
        elif isinstance(v, dict):
            for kk, vv in v.items():
                if isinstance(vv, str):
                    flat.setdefault(kk, vv)
    return flat


def _is_image_comp(key: str, comp: dict) -> bool:
    """组件是否是『图片』—— 图片不是 CSS 排版，克隆不了，套用时需用户换图。
    可靠信号：有 is_image 槽位，或 tag 是 <img>。（图注 image_caption 是文字，不算。）"""
    if "img" in (comp.get("tag") or ""):
        return True
    return any(isinstance(s, dict) and s.get("is_image") for s in (comp.get("slots") or {}).values())


def generate_preview_generic(components: dict, skeleton_dir: str = None) -> str:
    """通用预览：对任意 LLM 提取出的组件（{tag, style, sample}）逐个渲染成清单。
    不依赖固定组件名 —— 新组件（代码块/列表/卡片…）都能渲染。LLM 全包提取走这个。
    所有文本一律转义（描述里可能含 <p>/<strong> 这类标签举例，不转义会被浏览器当真标签执行）。"""
    import html as _h
    esc = _h.escape
    BOLD = {"bold", "600", "700", "800", "900"}
    # 容忍两种 schema：扁平 {_meta, <组件>...} 或 包了一层 {meta, components:{...}}
    if isinstance(components.get("components"), dict):
        _m = components.get("_meta") or components.get("meta") or {}
        components = {"_meta": _m, **components["components"]}
    # 根容器的基础样式（字体/字号/颜色/行高）—— 正文等组件继承它，预览必须把它套在外层，否则正文字体不对
    base = {}
    for _k, _c in components.items():
        if isinstance(_c, dict) and (_k in ("container", "root_wrapper", "root") or "container" in _k or "wrapper" in _k):
            base = _flatten_style(_c.get("style", {}))
            break
    base_sv = style_to_str({k: v for k, v in base.items()
                            if k in ("font-size", "font-family", "color", "line-height", "letter-spacing")})
    P = ['<!DOCTYPE html><html><head><meta charset="utf-8"><title>样式提取预览</title>',
         '<style>body{margin:0;background:#f5f5f5;font-family:-apple-system,sans-serif}',
         '.preview-wrap{max-width:720px;margin:20px auto;background:#fff;padding:40px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08)}',
         '.comp-label{font-size:11px;color:#999!important;text-transform:uppercase;letter-spacing:2px!important;margin:32px 0 8px;padding-top:16px;border-top:1px solid #eee;font-family:-apple-system,sans-serif!important}',
         '.comp-label:first-child{border-top:none;margin-top:0}',
         '.preview-wrap img{max-width:100%!important;height:auto!important;box-sizing:border-box}',  # 参考原图常很大，约束进容器、别跑出页面',
         f'</style></head><body><div class="preview-wrap" style="{base_sv}">',
         '<h1 style="font-size:20px;color:#333;margin:0 0 8px;font-family:-apple-system,sans-serif">提取样式预览</h1>',
         f'<p style="font-size:11px;color:#bbb;margin:0 0 8px;font-family:-apple-system">根容器基础样式: {esc(base_sv) or "⚠ 未提取到根容器（正文字体会不准）"}</p>']
    meta = components.get("_meta", {})
    if isinstance(meta, dict) and meta.get("visual_style"):
        P.append(f'<p style="font-size:13px;color:#999;margin:0 0 24px;">{esc(meta["visual_style"])}</p>')
    # 顶部诚实摘要：可克隆的 CSS 组件 vs 不可克隆的图片组件
    allc = [(k, c) for k, c in components.items() if not k.startswith("_") and isinstance(c, dict)]
    imgk = [k for k, c in allc if _is_image_comp(k, c)]
    if imgk:
        P.append(f'<p style="font-size:12px;color:#9a3412;background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:8px 10px;margin:0 0 20px;font-family:-apple-system">'
                 f'⚠ 本风格含 <b>{len(imgk)}</b> 个图片组件（{esc("、".join(imgk))}）——图片不是 CSS 排版、<b>克隆不了</b>，套你自己内容时需换图/重做。'
                 f'其余 <b>{len(allc)-len(imgk)}</b> 个是可克隆的 CSS 组件。</p>')
    for key, comp in components.items():
        if key.startswith("_") or not isinstance(comp, dict):
            continue
        if comp.get("skeleton_ref") and skeleton_dir:
            P.extend(_render_skeleton_components({key: comp}, skeleton_dir))
            continue
        warn = ('<p style="color:#9a3412;font-size:11px;margin:2px 0 6px;font-family:-apple-system">'
                '⚠ 图片组件 · 不是 CSS、克隆不了 —— 套你自己内容时换成你的图</p>') if _is_image_comp(key, comp) else ''
        if isinstance(comp.get("skeleton"), str):   # inline 骨架（LLM 提取的复合件）
            slots = comp.get("slots", {})
            def _sl(m, slots=slots):
                sd = slots.get(m.group(1), {}) if isinstance(slots, dict) else {}
                if isinstance(sd, dict) and sd.get("is_image"):
                    url = sd.get("src") or ""
                    if not url and isinstance(sd.get("sources"), list) and sd["sources"]:
                        url = sd["sources"][0] if isinstance(sd["sources"][0], str) else ""
                    if not url and isinstance(sd.get("example"), str):
                        url = sd["example"]
                    url = url if isinstance(url, str) and url.startswith("http") else ""
                    # 抓到真实图地址→显示参考原图（让你看见抓到了什么）；否则占位图（看图框样式）
                    return esc(url) if url else "https://placehold.co/600x360/eee/999?text=image"
                v = sd.get("example") or sd.get("default") or sd.get("from") or m.group(1)
                return esc(re.split(r'\s*(?:[（(]禁|←)', str(v))[0][:60])
            P.append(f'<p class="comp-label">{esc(comp.get("description", key))}</p>')
            if warn:
                P.append(warn)
            P.append(re.sub(r'\{\{(\w+)\}\}', _sl, comp["skeleton"]))
            continue
        desc = esc(comp.get("description", key))
        tagpath = comp.get("tag") or "p"
        tag = tagpath.split(">")[-1].split()[0].strip() or "p"
        is_nested = ">" in tagpath
        sample = esc(comp.get("sample") or "示例文字")
        flat = _flatten_style(comp.get("style", {}) or {})
        sv = style_to_str(flat)
        P.append(f'<p class="comp-label">{desc}</p>')
        if warn:
            P.append(warn)
        # 外层容器：只展示信息（不实际包裹）
        if key == "container" or "container" in key or tag in ("body",):
            P.append(f'<p style="font-size:12px;color:#666;">{esc(sv) or "(继承默认)"}</p>')
            continue
        # 图片：按 tag 判断（不靠 style 嵌套判断，否则会把嵌套标题误当图片）
        if "img" in tagpath or "image" in key:
            cs = style_to_str(comp.get("style", {}).get("container", {})) if isinstance(comp.get("style", {}).get("container"), dict) else ""
            P.append(f'<section style="{cs}"><img src="https://placehold.co/600x220/eee/999?text=image" style="max-width:100%;height:auto" /></section>')
            continue
        bold = ("strong" in tagpath) or (flat.get("font-weight") in BOLD)
        if tag in ("ul", "ol"):
            P.append(f'<{tag} style="{sv}"><li>{sample}</li><li>示例第二项</li></{tag}>')
        elif tag == "li":
            P.append(f'<ul style="padding-left:28px"><li style="{sv}">{sample}</li></ul>')
        elif not is_nested and tag in ("strong", "em", "code", "span", "b", "mark", "u") and "font-size" not in flat:
            # 纯行内强调（独立 inline 标签、无自己的大字号）→ 嵌进一句正文里展示
            P.append(f'<p style="font-size:16px;line-height:1.75">行内示例：<{tag} style="{sv}">{sample}</{tag}> 嵌在正文里。</p>')
        elif bold:
            # 标题/加粗块（含 section>p>strong 这种）→ 用扁平样式 + strong 渲染
            P.append(f'<p style="{sv}"><strong>{sample}</strong></p>')
        else:
            t = tag if tag.isalpha() else "p"
            P.append(f'<{t} style="{sv}">{sample}</{t}>')
    P.append('</div></body></html>')
    return "\n".join(P)


TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "templates")


def _slug(name: str) -> str:
    return re.sub(r'[^\w\-]', '-', name).strip('-') or "unnamed"


def build_style_inventory(js: str) -> str:
    """确定性 prep：每种 (tag, style) 去重计数 + 取样例文本 → 喂 LLM 归纳的清单。"""
    inv = OrderedDict()
    for m in re.finditer(r'<(\w+)\b[^>]*?\bstyle="([^"]*)"', js):
        tag = m.group(1)
        style = re.sub(r'\s+', ' ', unescape_html(m.group(2))).strip()
        if not style:
            continue
        gt = js.find('>', m.end())
        sample = clean_text(js[gt + 1:gt + 220])[:50] if gt != -1 else ""
        k = (tag, style)
        if k not in inv:
            inv[k] = [0, sample]
        inv[k][0] += 1
        if not inv[k][1] and sample:
            inv[k][1] = sample
    rows = sorted(inv.items(), key=lambda kv: -kv[1][0])
    out = [f"# 样式清单：{len(rows)} 种不同 tag+style（按出现次数降序）",
           "# 据此归纳组件。高频多半是正文/容器，低频大字号多半是标题/特殊件。\n"]
    for (tag, style), (cnt, samp) in rows:
        if cnt < 2 and len(style) < 12:
            continue
        out.append(f"[{tag}] ×{cnt}\n  style: {style}" + (f"\n  例: {samp}" if samp else ""))
    return "\n".join(out)


def build_cleaned_view(js: str) -> str:
    """清洗结构视图：去噪声属性、折叠空 span 与 svg，但**保住图片真实地址**（公众号图地址在 data-src，
    要留给提取去抓——用不用是套用时用户的决定）。"""
    c = js
    c = re.sub(r'\s+src="data:[^"]*"', '', c)        # 去掉懒加载的 base64 占位 src
    c = re.sub(r'\s+data-src=', ' src=', c)          # 真实图地址 data-src → src，保住
    c = re.sub(r'\s+(leaf|textstyle|data-[\w-]+|nodeleaf|powered-by|class|id|mpa-[\w-]+|hm_[\w-]+)="[^"]*"', '', c)
    c = re.sub(r'<span>\s*</span>', '', c)
    c = re.sub(r'<svg\b.*?</svg>', '<svg/>', c, flags=re.DOTALL)
    c = re.sub(r'>\s+<', '><', c)
    return c


def validate_template(components: dict) -> list:
    """机器校验提取出的模板（不信 subagent 自报）。返回问题列表，空=通过。"""
    issues = []
    if not isinstance(components, dict):
        return ["不是 JSON 对象"]
    if isinstance(components.get("components"), dict):
        issues.append("❌ schema 错：顶层多包了一层 'components'，应扁平展开（_meta + 各组件直接在顶层）")
        components = components["components"]
    if not any(k in components for k in ("_meta", "meta")):
        issues.append("缺 _meta")
    comps = {k: v for k, v in components.items() if not k.startswith("_") and isinstance(v, dict)}
    cont = comps.get("container") or comps.get("root_wrapper")
    if not cont:
        issues.append("❌ 缺 container 根容器（正文字体字号会全错）")
    elif "font-size" not in _flatten_style(cont.get("style", {})) and "font-family" not in _flatten_style(cont.get("style", {})):
        issues.append("container 没抓到 font-size/font-family（根容器基础字体丢了）")
    if not any("body" in k or c.get("tag") == "p" for k, c in comps.items()):
        issues.append("没有正文件（body_text）")
    if not any(("head" in k or "title" in k or "标题" in c.get("description", "")) for k, c in comps.items()):
        issues.append("没有标题件")
    for k, c in comps.items():
        sk = c.get("skeleton", "")
        if isinstance(sk, str) and sk:
            missing = set(re.findall(r'\{\{(\w+)\}\}', sk)) - set(c.get("slots", {}) or {})
            if missing:
                issues.append(f"{k}: skeleton 槽位 {sorted(missing)} 未在 slots 定义")
            blocks = len(re.findall(r'<(?:section|div)\b[^>]*?(?:border|padding):', sk))
            bs = len(re.findall(r'box-sizing:\s*border-box', sk))
            if blocks > bs:
                issues.append(f"{k}: {blocks} 个带 border/padding 的块但仅 {bs} 个 box-sizing（疑漏补）")
    if len(comps) < 3:
        issues.append(f"只提到 {len(comps)} 个组件，疑似提取不全")
    return issues


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else ""

    if cmd == "prep" and len(args) >= 3:
        url, slug = args[1], _slug(args[2])
        print(f"📥 抓取 {url}")
        js = extract_js_content(fetch_html(url))
        print(f"   js_content {len(js):,} 字符")
        inv_path = os.path.join(TEMPLATES_DIR, f"{slug}.inventory.txt")
        cln_path = os.path.join(TEMPLATES_DIR, f"{slug}.cleaned.html")
        open(inv_path, "w", encoding="utf-8").write(build_style_inventory(js))
        open(cln_path, "w", encoding="utf-8").write(build_cleaned_view(js))
        print(f"📋 样式清单 → {inv_path}\n🧱 清洗结构 → {cln_path}")
        print(f"\n下一步：subagent 读这两个文件 + SKILL.md「提取契约」→ 写 templates/{slug}.json，"
              f"再 `validate {slug}` / `render {slug}`。")

    elif cmd == "render" and len(args) >= 2:
        slug = _slug(args[1])
        comps = json.load(open(os.path.join(TEMPLATES_DIR, f"{slug}.json"), encoding="utf-8"))
        out = os.path.join(TEMPLATES_DIR, f"{slug}-preview.html")
        open(out, "w", encoding="utf-8").write(generate_preview_generic(comps, TEMPLATES_DIR))
        print(f"🖼  预览 → {out}")

    elif cmd == "validate" and len(args) >= 2:
        slug = _slug(args[1])
        comps = json.load(open(os.path.join(TEMPLATES_DIR, f"{slug}.json"), encoding="utf-8"))
        issues = validate_template(comps)
        if issues:
            print(f"❌ 校验未过（{len(issues)} 项）:")
            for i in issues:
                print("  -", i)
            sys.exit(1)
        n = len([k for k in (comps.get("components", comps)) if not k.startswith("_")])
        print(f"✅ 校验通过：{n} 个组件，schema/必备件/box-sizing 都 OK")

    else:
        print("用法:")
        print("  prep <url> <名>   抓取+样式清单+清洗结构（喂 LLM 归纳）")
        print("  validate <名>      机器校验 templates/<名>.json")
        print("  render <名>        从 <名>.json 出预览 HTML")
        print("\n提取由 subagent 读 prep 产物 + SKILL.md 提取契约完成（LLM 全包，正则已退役）。")
        sys.exit(1 if cmd else 0)


if __name__ == "__main__":
    main()
