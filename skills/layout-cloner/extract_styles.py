#!/usr/bin/env python3
"""
layout-cloner: 从公众号文章 HTML 自动提取常规组件的 inline style。
第一步只处理：容器、正文段落、三种强调、分节大数字标题、小标题、图片。

用法：python3 extract_styles.py <wechat_html_file_or_url>
输出：JSON 样式系统 + 可视化预览 HTML
"""

import json
import re
import sys
import subprocess
import tempfile
from html.parser import HTMLParser
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


# ── 3. 组件识别 & 样式提取 ────────────────────────

class StyleExtractor:
    """从 js_content HTML 中识别并提取各组件样式"""

    def __init__(self, content_html: str):
        self.html = content_html
        self.components = OrderedDict()

    def _detect_article_type(self) -> str:
        """检测文章排版类型"""
        textstyle_count = len(re.findall(r'<span textstyle=""', self.html))
        xiumi_count = len(re.findall(r'powered-by="xiumi\.us"', self.html))
        section_flex_count = len(re.findall(r'display:\s*flex', self.html))
        justify_p_count = len(re.findall(r'text-align:\s*justify', self.html))

        if textstyle_count > 20 and textstyle_count > section_flex_count * 3:
            return "textstyle"
        if xiumi_count > 3:
            return "xiumi"
        return "section"

    def extract_all(self) -> dict:
        article_type = self._detect_article_type()
        self.components["_meta"] = {
            "description": "文章元信息",
            "article_type": article_type
        }

        if article_type == "textstyle":
            self._extract_textstyle_all()
        elif article_type == "xiumi":
            self._extract_xiumi_all()
        else:
            self._extract_container()
            self._extract_body_text()
            self._extract_emphasis()
            self._extract_part_heading()
            self._extract_sub_heading()
            self._extract_tags()
            self._extract_content_padding()

        self._extract_image()
        return self.components

    # ══════════════════════════════════════════════
    #  textstyle 型文章提取（原生微信编辑器）
    # ══════════════════════════════════════════════

    def _extract_textstyle_all(self):
        """提取 textstyle span 型文章的所有组件"""
        from collections import Counter

        # ── 统计所有 textstyle span 的样式 ──
        span_styles = Counter()
        span_examples = {}
        for m in re.finditer(
            r'<span textstyle=""[^>]*style="([^"]+)"[^>]*>(.*?)</span>',
            self.html, re.DOTALL
        ):
            style_raw = re.sub(r'\s+', ' ', m.group(1).strip())
            text = clean_text(m.group(2))
            span_styles[style_raw] += 1
            if style_raw not in span_examples and text and len(text) > 1:
                span_examples[style_raw] = text[:40]

        # ── 段落样式 ──
        p_styles = Counter()
        for m in re.finditer(r'<p[^>]*style="([^"]+)"', self.html):
            s = re.sub(r'\s+', ' ', m.group(1).strip())
            if 'display: none' not in s:
                p_styles[s] += 1

        # ── 找基础 leaf span 样式（正文字体参数） ──
        leaf_styles = Counter()
        for m in re.finditer(
            r'<span leaf=""[^>]*style="([^"]+)"',
            self.html
        ):
            s = re.sub(r'\s+', ' ', m.group(1).strip())
            leaf_styles[s] += 1

        # 从最常见的 leaf span 提取正文基础样式
        if leaf_styles:
            most_common_leaf = leaf_styles.most_common(1)[0][0]
            leaf_parsed = parse_style(most_common_leaf)
            self.components["body_base"] = {
                "description": "正文基础字体（leaf span 上）",
                "tag": "span leaf",
                "style": {
                    "font-size": leaf_parsed.get("font-size", "17px"),
                    "font-family": leaf_parsed.get("font-family", ""),
                    "color": leaf_parsed.get("color", "rgba(0,0,0,0.9)"),
                    "line-height": leaf_parsed.get("line-height", "1.6"),
                    "letter-spacing": leaf_parsed.get("letter-spacing", "0.034em"),
                },
                "sample": ""
            }

        # 段落间距
        if p_styles:
            most_common_p = p_styles.most_common(1)[0][0]
            p_parsed = parse_style(most_common_p)
            margin_l = p_parsed.get("margin-left", "")
            margin_r = p_parsed.get("margin-right", "")
            margin = p_parsed.get("margin", "")
            self.components["paragraph"] = {
                "description": "正文段落",
                "tag": "p",
                "style": p_parsed,
                "sample": f"出现 {p_styles.most_common(1)[0][1]} 次"
            }

        # ── 分类 textstyle span 为不同组件 ──
        # 按 background-color 和 font-size 分组
        style_groups = {}
        for style_raw, count in span_styles.most_common(20):
            parsed = parse_style(style_raw)
            bg = parsed.get("background-color", "")
            color = parsed.get("color", "")
            fs = parsed.get("font-size", "14px")
            fw = parsed.get("font-weight", "")

            # 纯正文（无背景色、无加粗、小字号）
            if not bg and fw != "bold" and fs in ("14px", "15px", "16px"):
                if "body_text" not in self.components:
                    self.components["body_text"] = {
                        "description": "正文文字",
                        "tag": "span textstyle",
                        "style": parsed,
                        "count": count,
                        "sample": span_examples.get(style_raw, "")
                    }
                continue

            # 有背景色 → 色块标签
            if bg:
                # 给它起个名字
                fs_num = int(re.sub(r'\D', '', fs) or 14)
                if fs_num >= 40:
                    name = "splash_headline"
                    desc = f"爆炸大标题（{bg} 底 + {color} 字）"
                elif fs_num >= 18:
                    name = f"tag_{bg.replace(' ','').replace(',','_').replace('(','').replace(')','')}"
                    desc = f"色块标签（{bg} 底 + {color} 字）"
                else:
                    name = f"inline_tag_{bg.replace(' ','').replace(',','_').replace('(','').replace(')','')}"
                    desc = f"行内标签（{bg} 底 + {color} 字）"

                # 避免重名
                if name in self.components:
                    name = f"{name}_{count}"

                self.components[name] = {
                    "description": desc,
                    "tag": "span textstyle",
                    "style": parsed,
                    "count": count,
                    "sample": span_examples.get(style_raw, "")
                }
                continue

            # 无背景色但有特殊颜色或加粗
            if color and color not in ("rgb(0, 0, 0)", "rgba(0, 0, 0, 0.9)") or fw == "bold":
                name = f"emphasis_{color.replace(' ','').replace(',','_').replace('(','').replace(')','')}"
                if name in self.components:
                    name = f"{name}_{count}"
                self.components[name] = {
                    "description": f"强调文字（{color} + {fw}）",
                    "tag": "span textstyle",
                    "style": parsed,
                    "count": count,
                    "sample": span_examples.get(style_raw, "")
                }

    # ══════════════════════════════════════════════
    #  xiumi 模板型文章提取（秀米编辑器）
    # ══════════════════════════════════════════════

    def _extract_xiumi_all(self):
        """提取秀米模板文章的组件。

        关键原则：
        - 正文色从 <p><span leaf=""> 内容层判断，不用全局 color 频率（装饰色会干扰）
        - 卡片结构要识别 border + box-shadow 组合，不只是 background-color
        - 色板标注语义角色（边框/阴影/背景/装饰文字）
        """
        from collections import Counter
        import html as html_mod

        # ── 收集所有有视觉样式的元素 ──
        bg_colors = Counter()
        border_colors = Counter()
        shadow_colors = Counter()
        font_sizes = Counter()
        text_colors = Counter()
        # 单独统计内容层文字色（<span leaf=""> 的父级 section 的 color）
        content_text_colors = Counter()

        for m in re.finditer(r'style="([^"]{15,})"', self.html):
            style = html_mod.unescape(m.group(1))
            bg = re.search(r'background-color:\s*([^;\"]+)', style)
            if bg:
                v = bg.group(1).strip()
                if v not in ('rgb(255, 255, 255)', 'rgba(255, 255, 255, 0)', 'transparent'):
                    bg_colors[v] += 1
            bc = re.search(r'border-color:\s*([^;\"]+)', style)
            if bc:
                val = bc.group(1).strip()
                # 排除 border-box 误匹配 和 box-sizing 属性
                if 'border-box' not in val and 'box-sizing' not in val:
                    border_colors[val] += 1
            # box-shadow 颜色
            bs = re.search(r'box-shadow:\s*(rgb\([^)]+\))', style)
            if bs:
                shadow_colors[bs.group(1).strip()] += 1
            fs = re.search(r'font-size:\s*(\d+)px', style)
            if fs and int(fs.group(1)) > 0:
                font_sizes[f"{fs.group(1)}px"] += 1
            col = re.search(r'(?<![a-z-])color:\s*(rgb[^;\"]+)', style)
            if col:
                text_colors[col.group(1).strip()] += 1

        # 内容层文字色：找包含 <span leaf=""> 正文的 section 的 font-size
        # 秀米正文通常在 <section style="...font-size:14px..."><p><span leaf="">
        for m in re.finditer(
            r'<section[^>]*style="([^"]*font-size:\s*(\d+)px[^"]*)"[^>]*>'
            r'(?:\s*<p[^>]*>)?\s*<span\s+leaf=""',
            self.html
        ):
            fs_num = int(m.group(2))
            if fs_num <= 18:  # 正文字号不会超过 18px
                style = html_mod.unescape(m.group(1))
                col = re.search(r'(?<![a-z-])color:\s*(rgb[^;\"]+)', style)
                if col:
                    content_text_colors[col.group(1).strip()] += 1
                else:
                    content_text_colors["inherit"] += 1

        # ── 提取主色系（带语义角色） ──
        palette = {}
        for color, count in bg_colors.most_common(5):
            palette[color] = {"color": color, "count": count, "roles": ["background"]}
        for color, count in border_colors.most_common(3):
            if color in palette:
                palette[color]["roles"].append("border")
            else:
                palette[color] = {"color": color, "count": count, "roles": ["border"]}
        for color, count in shadow_colors.most_common(3):
            if color in palette:
                palette[color]["roles"].append("shadow")
            else:
                palette[color] = {"color": color, "count": count, "roles": ["shadow"]}
        # 装饰文字色（出现在标题/标签里但不是正文色的）
        for color, count in text_colors.most_common(5):
            if color in palette:
                palette[color]["roles"].append("text")

        palette_list = sorted(palette.values(), key=lambda x: x["count"], reverse=True)
        self.components["color_palette"] = {
            "description": f"色系（{len(palette_list)} 色）",
            "tag": "section",
            "style": {},
            "palette": [
                {"color": p["color"], "count": p["count"], "role": "+".join(p["roles"])}
                for p in palette_list
            ],
            "sample": ", ".join(p["color"] for p in palette_list[:4])
        }

        # ── 正文字体（从内容层判断，不用全局频率） ──
        if font_sizes:
            body_fs = font_sizes.most_common(1)[0][0]
            # 正文色：优先用内容层统计，如果是 inherit 则默认黑色
            if content_text_colors:
                body_color_raw = content_text_colors.most_common(1)[0][0]
                body_color = body_color_raw if body_color_raw != "inherit" else "rgb(0, 0, 0)"
            else:
                body_color = "rgb(0, 0, 0)"
            self.components["body_text"] = {
                "description": "正文文字",
                "tag": "section",
                "style": {"font-size": body_fs, "color": body_color},
                "sample": f"出现 {font_sizes.most_common(1)[0][1]} 次",
                "note": "色从内容层 <span leaf=> 父级推断，非全局频率"
            }

        # ── 大标题元素（含 text-shadow） ──
        for m in re.finditer(r'<section[^>]*style="([^"]*font-size:\s*(\d+)px[^"]*)"[^>]*>', self.html):
            fs_num = int(m.group(2))
            if fs_num >= 40:
                style_str = html_mod.unescape(m.group(1))
                style = parse_style(style_str)
                after = self.html[m.end():m.end()+300]
                text_m = re.search(r'>([^<]{1,})<', after)
                text = clean_text(text_m.group(1)) if text_m else ""
                name = f"headline_{fs_num}px"
                if name not in self.components:
                    headline_style = {
                        "font-size": f"{fs_num}px",
                        "color": style.get("color", ""),
                    }
                    # 保留 text-shadow（秀米常用双色阴影做视觉层次）
                    if "text-shadow" in style:
                        headline_style["text-shadow"] = style["text-shadow"]
                    if "letter-spacing" in style:
                        headline_style["letter-spacing"] = style["letter-spacing"]
                    if "line-height" in style:
                        headline_style["line-height"] = style["line-height"]
                    self.components[name] = {
                        "description": f"大标题（{fs_num}px）",
                        "tag": "section",
                        "style": headline_style,
                        "sample": text
                    }

        # ── 卡片框架结构（border + box-shadow 组合） ──
        # 这是秀米文章的核心视觉——识别 border + box-shadow 的组合卡片
        for m in re.finditer(
            r'<section[^>]*style="([^"]*border-(?:width|style)[^"]*box-shadow[^"]*)"[^>]*>',
            self.html
        ):
            style_str = html_mod.unescape(m.group(1))
            style = parse_style(style_str)
            # 需要同时有 border 和 box-shadow
            has_border = ("border-width" in style or "border-style" in style
                          or "border" in style)
            has_shadow = "box-shadow" in style
            if has_border and has_shadow:
                shadow_val = style.get("box-shadow", "")
                # 跳过 0px 0px 0px 的无效阴影
                if "0px 0px 0px" in shadow_val and shadow_val.count("0px") >= 3:
                    continue
                # 提取卡片框架样式
                card_frame = {}
                for prop in ("border-width", "border-style", "border-color",
                             "border", "padding", "box-shadow"):
                    if prop in style:
                        card_frame[prop] = style[prop]
                # 找卡片内部背景区
                after = self.html[m.end():m.end()+500]
                inner_bg_m = re.search(r'background-color:\s*([^;\"]+)', after)
                inner_padding_m = re.search(r'padding:\s*([^;\"]+)', after)
                card_inner = {}
                if inner_bg_m:
                    card_inner["background-color"] = inner_bg_m.group(1).strip()
                if inner_padding_m:
                    card_inner["padding"] = inner_padding_m.group(1).strip()

                # 找卡片外层宽度
                # 回退找父级 section 的 width
                before = self.html[max(0, m.start()-300):m.start()]
                width_m = re.search(r'width:\s*(\d+%)', before[::-1][:200][::-1])

                self.components["card_frame"] = {
                    "description": "内容卡片框架（border + box-shadow 组合）",
                    "tag": "section",
                    "style": {
                        "frame": card_frame,
                        "inner": card_inner,
                    },
                    "sample": "核心视觉组件"
                }
                break

        # ── 品牌标签（背景色 + 对比文字色的 inline 标签） ──
        for m in re.finditer(
            r'<span[^>]*style="([^"]*background-color[^"]*)"[^>]*>(.*?)</span>',
            self.html, re.DOTALL
        ):
            text = clean_text(m.group(2))
            if text and len(text) < 20:
                style = parse_style(m.group(1))
                bg = style.get("background-color", "")
                # 找父级的 color
                before = self.html[max(0, m.start()-300):m.start()]
                parent_color_m = re.search(r'color:\s*(rgb[^;\"]+)', before[::-1][:200][::-1])
                if bg and parent_color_m:
                    self.components["brand_label"] = {
                        "description": f"品牌标签（{bg} 底 + 对比色字）",
                        "tag": "span",
                        "style": {
                            "background-color": bg,
                            "font-weight": style.get("font-weight", "bold"),
                        },
                        "parent_color": parent_color_m.group(1).strip() if parent_color_m else "",
                        "sample": text
                    }
                    break

        # ── 分隔条（小高度 + 背景色 + overflow:hidden，宽度接近全宽） ──
        for m in re.finditer(
            r'<section[^>]*style="([^"]*)"[^>]*>',
            self.html
        ):
            style_str = html_mod.unescape(m.group(1))
            style = parse_style(style_str)
            h_str = style.get("height", "")
            overflow = style.get("overflow", "")
            bg = style.get("background-color", "")
            width = style.get("width", "100%")
            h_match = re.match(r'(\d+)px', h_str)
            if not h_match or overflow != "hidden":
                continue
            h = int(h_match.group(1))
            # 分隔条：高度小、有背景色、宽度接近全宽（非 5px 之类的小装饰）
            w_match = re.match(r'(\d+)', width)
            if w_match and int(w_match.group(1)) < 50:
                continue  # 跳过窄装饰元素
            if 3 <= h <= 15 and bg:
                self.components["separator_bar"] = {
                    "description": f"分隔条（{h}px 高）",
                    "tag": "section",
                    "style": {
                        "height": h_str,
                        "overflow": "hidden",
                        "background-color": bg,
                    },
                    "sample": ""
                }
                # 保留边框信息（如果有）
                for prop in ("border-style", "border-width", "border-color"):
                    if prop in style:
                        self.components["separator_bar"]["style"][prop] = style[prop]
                break

        # ── CTA 区块（大面积背景色 + 边框的区域） ──
        for m in re.finditer(
            r'<section[^>]*style="([^"]*background-color[^"]*border-(?:style|width)[^"]*)"[^>]*>',
            self.html
        ):
            style_str = html_mod.unescape(m.group(1))
            style = parse_style(style_str)
            bg = style.get("background-color", "")
            # CTA 通常有边框且不是内容卡片（没有 box-shadow）
            if bg and "box-shadow" not in style:
                border_w = style.get("border-width", "")
                border_c = style.get("border-color", "")
                if border_w and int(re.sub(r'\D', '', border_w) or 0) >= 3:
                    after = self.html[m.end():m.end()+500]
                    text_m = re.search(r'<span\s+leaf="">([^<]+)</span>', after)
                    text = text_m.group(1).strip() if text_m else ""
                    self.components["cta_bar"] = {
                        "description": f"CTA 区块（{bg} 底 + {border_c} 边框）",
                        "tag": "section",
                        "style": {
                            "background-color": bg,
                            "border-style": style.get("border-style", "solid"),
                            "border-width": border_w,
                            "border-color": border_c,
                        },
                        "sample": text
                    }
                    break

        # ── 扁平色块/卡片（仅 background-color，无 border+shadow） ──
        seen_bgs = set()
        for color, count in bg_colors.most_common(5):
            if color in seen_bgs:
                continue
            seen_bgs.add(color)
            pattern = rf'background-color:\s*{re.escape(color)}'
            sample = ""
            for m2 in re.finditer(pattern, self.html):
                after = self.html[m2.end():m2.end()+500]
                text_m = re.search(r'>([^<]{5,})<', after)
                if text_m:
                    sample = clean_text(text_m.group(1))[:40]
                    break
            slug = re.sub(r'[^\w]', '_', color)
            self.components[f"card_{slug}"] = {
                "description": f"色块/卡片（{color}）",
                "tag": "section",
                "style": {"background-color": color},
                "count": count,
                "sample": sample
            }

    # ══════════════════════════════════════════════
    #  section 嵌套型文章提取（绿色科技风等）
    # ══════════════════════════════════════════════

    def _find_all_styled(self, tag: str, pattern_in_style: str = None) -> list:
        """找所有带 style 的指定标签，返回 [(style_str, inner_html), ...]"""
        regex = rf"<{tag}\b[^>]*?style=\"([^\"]*?)\"[^>]*?>(.*?)</{tag}>"
        results = []
        for m in re.finditer(regex, self.html, re.DOTALL):
            style_str, inner = m.group(1), m.group(2)
            if pattern_in_style and pattern_in_style not in style_str:
                continue
            results.append((style_str, inner, m.start()))
        return results

    def _find_all_tags(self, tag: str) -> list:
        """找所有指定标签（含自闭合），返回 [(full_match, style_str, pos), ...]"""
        # 匹配自闭合和非自闭合
        regex = rf"<{tag}\b([^>]*?)(?:/>|>(.*?)</{tag}>)"
        results = []
        for m in re.finditer(regex, self.html, re.DOTALL):
            attrs = m.group(1)
            style_m = re.search(r'style="([^"]*)"', attrs)
            style_str = style_m.group(1) if style_m else ""
            results.append((m.group(0), style_str, m.start()))
        return results

    # ── 容器 ──
    def _extract_container(self):
        # 第一个带 max-width 的 section/div
        m = re.search(
            r'<section[^>]*?style="([^"]*max-width[^"]*)"',
            self.html
        )
        if m:
            style = parse_style(m.group(1))
            self.components["container"] = {
                "description": "外层容器",
                "tag": "div",
                "style": style,
                "sample": ""
            }

    # ── 正文段落 ──
    def _extract_body_text(self):
        # 找正文 <p>：有 font-size + line-height + text-align:justify
        candidates = self._find_all_styled("p", "text-align:justify")
        # 取出现最多的样式组合
        style_counts = {}
        for style_str, inner, _ in candidates:
            s = parse_style(style_str)
            # 只保留排版相关属性
            key_props = {k: v for k, v in s.items()
                         if k in ("font-size", "line-height", "color", "text-align",
                                  "margin", "margin-bottom", "letter-spacing")}
            key = json.dumps(key_props, sort_keys=True)
            style_counts[key] = style_counts.get(key, 0) + 1

        if style_counts:
            most_common = max(style_counts, key=style_counts.get)
            style = json.loads(most_common)
            # 如果正文没有 color，从容器继承
            if "color" not in style and "container" in self.components:
                style["color"] = self.components["container"]["style"].get("color", "")
            # 取一个示例文本
            sample = ""
            for style_str, inner, _ in candidates:
                txt = clean_text(inner)
                if 20 < len(txt) < 200:
                    sample = txt[:80]
                    break
            self.components["body_text"] = {
                "description": "正文段落",
                "tag": "p",
                "style": style,
                "sample": sample
            }

    # ── 三种强调 ──
    def _extract_emphasis(self):
        # ① 彩色加粗 <strong style="color:...">
        strongs = self._find_all_styled("strong", "color:")
        if strongs:
            style = parse_style(strongs[0][0])
            sample = clean_text(strongs[0][1])
            self.components["emphasis_bold_color"] = {
                "description": "彩色加粗强调（核心概念）",
                "tag": "strong",
                "style": style,
                "sample": sample
            }

        # ② 渐变底色高亮 <span style="background:linear-gradient...">
        highlights = self._find_all_styled("span", "linear-gradient")
        if highlights:
            style = parse_style(highlights[0][0])
            sample = clean_text(highlights[0][1])
            self.components["emphasis_highlight"] = {
                "description": "渐变底色高亮（数字/关键词）",
                "tag": "span",
                "style": style,
                "sample": sample
            }

        # ③ 下划线强调 <span style="border-bottom:...">
        underlines = self._find_all_styled("span", "border-bottom:")
        # 排除非强调用途（如金句卡内的）
        for style_str, inner, _ in underlines:
            s = parse_style(style_str)
            if "font-weight" in s and "border-bottom" in s and "font-size" not in s:
                sample = clean_text(inner)
                self.components["emphasis_underline"] = {
                    "description": "下划线强调（专有名词）",
                    "tag": "span",
                    "style": s,
                    "sample": sample
                }
                break

    # ── 分节大数字标题 (01 PART | 中文 / ENGLISH) ──
    def _extract_part_heading(self):
        # 找 flex 布局 + 含 28px 大数字的 section
        pattern = (
            r'<section[^>]*?style="([^"]*display:\s*flex[^"]*align-items:\s*center'
            r'[^"]*gap[^"]*)"[^>]*>'
            r'(.*?)</section>\s*</section>'
        )
        matches = list(re.finditer(pattern, self.html, re.DOTALL))

        for m in matches:
            inner = m.group(2)
            if "28px" in inner and "font-weight:900" in inner:
                container_style = parse_style(m.group(1))

                # 提取大数字样式
                num_m = re.search(r'font-size:28px[^"]*font-weight:900[^"]*color:([^;]+)', inner)
                # 提取中文标题样式
                title_m = re.search(r'font-size:17px[^"]*font-weight:900[^"]*color:([^;]+)', inner)
                # 提取英文副标题
                en_m = re.search(r'font-size:11px[^"]*font-weight:600[^"]*color:([^;]+)', inner)
                # 提取分隔线
                sep_m = re.search(r'width:1px;height:(\d+px);background:([^;]+)', inner)

                # 提取完整子样式
                num_style_m = re.search(
                    r'<p[^>]*style="([^"]*font-size:28px[^"]*)"', inner)
                title_style_m = re.search(
                    r'<p[^>]*style="([^"]*font-size:17px[^"]*)"', inner)
                en_style_m = re.search(
                    r'<p[^>]*style="([^"]*font-size:11px[^"]*)"', inner)

                self.components["part_heading"] = {
                    "description": "分节大数字标题（01 PART | 中文标题 / ENGLISH）",
                    "tag": "section",
                    "style": container_style,
                    "sub_styles": {
                        "number": parse_style(num_style_m.group(1)) if num_style_m else {},
                        "title": parse_style(title_style_m.group(1)) if title_style_m else {},
                        "english": parse_style(en_style_m.group(1)) if en_style_m else {},
                        "separator": {
                            "width": "1px",
                            "height": sep_m.group(1) if sep_m else "36px",
                            "background": sep_m.group(2) if sep_m else "#E5E7EB"
                        }
                    },
                    "sample": "01 PART | 灵感 · 从抖音到游戏 / INSPIRATION"
                }
                break

    # ── 小标题 ──
    def _extract_sub_heading(self):
        # 方式1: <h4> 标签（可能带 border-left 竖条，也可能是纯粗体）
        h4s = self._find_all_styled("h4")
        for style_str, inner, _ in h4s:
            s = parse_style(style_str)
            if "font-weight" in s:
                has_border = "border-left" in s
                desc = "小标题（h4 + 左竖条）" if has_border else "小标题（h4 粗体）"
                self.components["sub_heading_h4"] = {
                    "description": desc,
                    "tag": "h4",
                    "style": s,
                    "sample": clean_text(inner)
                }
                break

        # 方式2: <p> 内含 background:linear-gradient(180deg,...) 的 span（黄底标注式小标题）
        gradient_180_pattern = r'<p[^>]*style="([^"]*font-weight:900[^"]*)"[^>]*>\s*<span[^>]*style="([^"]*linear-gradient\(180deg[^"]*)"'
        gm = re.search(gradient_180_pattern, self.html)
        if gm:
            p_style = parse_style(gm.group(1))
            span_style = parse_style(gm.group(2))
            self.components["sub_heading_highlight"] = {
                "description": "小标题（黄底渐变标注式）",
                "tag": "p > span",
                "style": {"p": p_style, "span": span_style},
                "sample": "第一层：时间窗"
            }

    # ── 标签胶囊（绿色圆角 + 黑色步骤） ──
    def _extract_tags(self):
        # 绿色标签胶囊：border-radius:999px + 主题色
        for m in re.finditer(
            r'<span[^>]*style="([^"]*border-radius:\s*999px[^"]*)"[^>]*>(.*?)</span>',
            self.html, re.DOTALL
        ):
            text = clean_text(m.group(2))
            if text and len(text) < 30:
                s = parse_style(m.group(1))
                self.components["tag_capsule"] = {
                    "description": "内容标签胶囊（绿色圆角）",
                    "tag": "span",
                    "style": s,
                    "sample": text
                }
                break

        # 黑色步骤标签：background 深色 + 白字 + 小字号
        for m in re.finditer(
            r'<span[^>]*style="([^"]*background:#[0-9a-fA-F]{3,6}[^"]*color:#fff[^"]*)"[^>]*>(.*?)</span>',
            self.html, re.DOTALL
        ):
            text = clean_text(m.group(2))
            s = parse_style(m.group(1))
            fs = s.get("font-size", "")
            if text and "STEP" in text.upper() or (fs and int(re.sub(r'\D', '', fs) or 99) <= 12):
                self.components["tag_step"] = {
                    "description": "步骤标签（深色底 + 白字）",
                    "tag": "span",
                    "style": s,
                    "sample": text
                }
                break

    # ── 内容区 padding（section 层的 padding） ──
    def _extract_content_padding(self):
        # 找包裹正文段落的 section 的 padding
        pattern = r'<section[^>]*style="([^"]*padding:\s*0\s+\d+px[^"]*)"[^>]*>'
        counts = {}
        for m in re.finditer(pattern, self.html):
            s = parse_style(m.group(1))
            pad = s.get("padding", "")
            if pad:
                counts[pad] = counts.get(pad, 0) + 1
        if counts:
            most_common = max(counts, key=counts.get)
            self.components["content_padding"] = {
                "description": "内容区水平 padding（section 层）",
                "tag": "section",
                "style": {"padding": most_common},
                "sample": f"出现 {counts[most_common]} 次"
            }

    # ── 图片 ──
    def _extract_image(self):
        container_style = {}
        frame_style = {}
        img_style = {}

        # 策略1: 找有 border 的 section，且内部包含 img
        # 匹配分写 border-width/border-style 和简写 border: Npx solid ...
        for m in re.finditer(
            r'<section[^>]*style="([^"]*(?:border-(?:width|style)|border:\s*\d+px\s+solid)[^"]*)"[^>]*>',
            self.html
        ):
            sec_style_str = m.group(1)
            # 检查后面 3000 字符内有没有 img
            after = self.html[m.end():m.end() + 3000]
            if '<img' not in after and 'data-src' not in after:
                continue
            sec_style = parse_style(sec_style_str)
            has_border = (
                ("border-width" in sec_style and "border-style" in sec_style) or
                any(k == "border" and "solid" in v for k, v in sec_style.items())
            )
            if has_border:
                bw = sec_style.get("border-width", "")
                bs = sec_style.get("border-style", "")
                bc = sec_style.get("border-color", "")
                br = sec_style.get("border-radius", "")
                frame_style = {
                    "border": sec_style.get("border", f"{bw} {bs} {bc}".strip()),
                    "border-radius": br,
                    "padding": sec_style.get("padding", ""),
                }
                frame_style = {k: v for k, v in frame_style.items() if v}
                break

        # 策略2: 找 text-align:center 的直接图片容器
        for m in re.finditer(
            r'<section[^>]*style="([^"]*text-align:\s*center[^"]*)"[^>]*>(.*?)</section>',
            self.html, re.DOTALL
        ):
            inner = m.group(2)
            if 'data-src' in inner and '<img' in inner:
                container_style = parse_style(m.group(1))
                img_m = re.search(r'<img[^>]*style="([^"]*)"', inner)
                if img_m:
                    img_style = parse_style(img_m.group(1))
                break

        # 如果没找到 container 但找到了 frame，从 frame 后面找 img style
        if not img_style:
            for m in re.finditer(r'<img[^>]*data-src[^>]*style="([^"]*)"', self.html):
                img_style = parse_style(m.group(1))
                break

        self.components["image"] = {
            "description": "图片（含容器）",
            "tag": "section > img",
            "style": {
                "container": container_style,
                "frame": frame_style,
                "img": img_style
            },
            "sample": "[图片]"
        }


# ── 3b. JSON → 样式模板（可复用速查表）────────────

def json_to_style_template(components: dict, theme_name: str) -> str:
    """把 components dict 转换成类似 wechat-green.html 注释块的样式速查文本。"""
    c = components
    lines = []
    a = lines.append
    article_type = c.get("_meta", {}).get("article_type", "section")

    # ── textstyle 型速查表 ──
    if article_type == "textstyle":
        a(f"<!--")
        a(f"  微信公众号 HTML 样式系统 — {theme_name}")
        a(f"  排版类型: textstyle span（原生微信编辑器）")
        if "body_base" in c:
            bs = c["body_base"]["style"]
            a(f"  基础字体: {bs.get('font-family', '系统默认')}")
            a(f"  基础字号: {bs.get('font-size', '17px')}, 行高: {bs.get('line-height', '1.6')}")
        a(f"")
        a(f"  使用方法: 把内容套进对应样式，所有样式 inline，直接粘公众号。")
        a(f"  本文排版特点: 样式写在 <span textstyle> 上，用色块标签做视觉层级。")
        a(f"")
        a(f"  ========== 样式速查 ==========")
        a(f"")

        if "paragraph" in c:
            ps = style_to_str(c["paragraph"]["style"])
            a(f'  【段落】')
            a(f'  <p style="{ps}">段落文字</p>')
            a(f"")

        if "body_text" in c:
            ss = style_to_str(c["body_text"]["style"])
            a(f'  【正文文字】= 最常见的行内文字样式')
            a(f'  <span style="{ss}">正文</span>')
            a(f"")

        # 色系（xiumi）
        if "color_palette" in c:
            palette = c["color_palette"].get("palette", [])
            a(f'  【色系】')
            for p in palette:
                a(f'    {p["role"]}: {p["color"]} (x{p["count"]})')
            a(f"")

        skip_keys = {"_meta", "container", "image", "paragraph", "body_base", "body_text", "color_palette"}
        for key, comp in c.items():
            if key in skip_keys:
                continue
            s = comp.get("style", {})
            if not s:
                continue
            ss = style_to_str(s)
            desc = comp.get("description", key)
            count = comp.get("count", 0)
            a(f'  【{desc}】出现 {count} 次')
            a(f'  <span style="{ss}">文字</span>')
            a(f"")

        if "image" in c:
            cs = style_to_str(c["image"]["style"].get("container", {}))
            ims = style_to_str(c["image"]["style"].get("img", {}))
            a(f'  【图片】')
            a(f'  <section style="{cs}">')
            a(f'    <img src="图片路径" style="max-width:100%;height:auto;{ims}" />')
            a(f'  </section>')
            a(f"")

        a(f"-->")
        return "\n".join(lines)

    # ── section 嵌套型速查表 ──

    # 提取主题色（从 emphasis_bold_color 或 tag_capsule）
    theme_color = ""
    for key in ("emphasis_bold_color", "tag_capsule"):
        if key in c:
            theme_color = c[key]["style"].get("color", "")
            if theme_color:
                break

    a(f"<!--")
    a(f"  微信公众号 HTML 样式系统 — {theme_name}")
    if theme_color:
        a(f"  主题色: {theme_color}")
    if "emphasis_highlight" in c:
        hl_bg = c["emphasis_highlight"]["style"].get("background", "")
        a(f"  高亮底色: {hl_bg}")
    if "container" in c:
        cs = c["container"]["style"]
        a(f"  字体: {cs.get('font-family', '系统默认')}")
    a(f"")
    a(f"  使用方法: 把内容套进对应样式，所有样式 inline，直接粘公众号。")
    a(f"")
    a(f"  ========== 样式速查 ==========")
    a(f"")

    # ── 容器
    if "container" in c:
        s = c["container"]["style"]
        ss = style_to_str(s)
        a(f'  【容器】')
        a(f'  <div style="{ss}">')
        a(f"")

    # ── 内容区 padding
    if "content_padding" in c:
        pad = c["content_padding"]["style"]["padding"]
        a(f'  【内容区 padding】每段正文/图片外层 section 统一加')
        a(f'  <section style="padding:{pad};">内容</section>')
        a(f"")

    # ── 正文段落
    if "body_text" in c:
        s = c["body_text"]["style"]
        ss = style_to_str(s)
        a(f'  【正文段落】')
        a(f'  <p style="{ss}">文字</p>')
        a(f"")

    # ── 强调
    if "emphasis_bold_color" in c:
        ss = style_to_str(c["emphasis_bold_color"]["style"])
        a(f'  ── 正文强调（套在段落内关键词上，一段最多 1-2 处）──')
        a(f'  【① 彩色加粗】= 核心概念 / 产品名 / 关键结论')
        a(f'  <strong style="{ss}">重点概念</strong>')
        a(f"")

    if "emphasis_highlight" in c:
        ss = style_to_str(c["emphasis_highlight"]["style"])
        a(f'  【② 渐变底色高亮】= 数字 / 最该一眼被看到的关键词')
        a(f'  <span style="{ss}">关键词</span>')
        a(f"")

    if "emphasis_underline" in c:
        ss = style_to_str(c["emphasis_underline"]["style"])
        a(f'  【③ 下划线强调】= 次级强调 / 专有名词')
        a(f'  <span style="{ss}">专有名词</span>')
        a(f"")

    # ── 分节大数字标题
    if "part_heading" in c:
        ph = c["part_heading"]
        cs = style_to_str(ph["style"])
        ns = style_to_str(ph["sub_styles"]["number"])
        ts = style_to_str(ph["sub_styles"]["title"])
        es = style_to_str(ph["sub_styles"]["english"])
        sep = ph["sub_styles"]["separator"]
        sep_s = style_to_str(sep)
        a(f'  【分节标题（大数字 + 竖线 + 中文标题 + 英文副标题）】')
        a(f'  <section style="{cs}">')
        a(f'    <section style="text-align:center;flex-shrink:0;">')
        a(f'      <p style="{ns}">01</p>')
        a(f'      <p style="margin:0;font-size:8px;font-weight:700;color:#D1D5DB;letter-spacing:2px;">PART</p>')
        a(f'    </section>')
        a(f'    <span style="{sep_s};flex-shrink:0;display:inline-block;"></span>')
        a(f'    <section>')
        a(f'      <p style="{ts}">中文标题</p>')
        a(f'      <p style="{es}">ENGLISH</p>')
        a(f'    </section>')
        a(f'  </section>')
        a(f"")

    # ── 小标题
    if "sub_heading_h4" in c:
        ss = style_to_str(c["sub_heading_h4"]["style"])
        desc = c["sub_heading_h4"]["description"]
        a(f'  【{desc}】')
        a(f'  <h4 style="{ss}">小标题</h4>')
        a(f"")

    if "sub_heading_highlight" in c:
        sh = c["sub_heading_highlight"]["style"]
        ps = style_to_str(sh["p"])
        ss = style_to_str(sh["span"])
        a(f'  【小标题（黄底渐变标注式）】')
        a(f'  <p style="{ps}"><span style="{ss}">小标题文字</span></p>')
        a(f"")

    # ── 步骤标签
    if "tag_step" in c:
        ss = style_to_str(c["tag_step"]["style"])
        a(f'  【步骤标签（深色底 + 白字）】= STEP 编号，常与 h4 小标题组合使用')
        a(f'  <section style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">')
        a(f'    <span style="{ss}">STEP 01</span>')
        if "sub_heading_h4" in c:
            h4s = style_to_str(c["sub_heading_h4"]["style"])
            a(f'    <h4 style="{h4s}">步骤标题</h4>')
        a(f'  </section>')
        a(f"")

    # ── 标签胶囊
    if "tag_capsule" in c:
        ss = style_to_str(c["tag_capsule"]["style"])
        a(f'  【内容标签胶囊】= 标注某段属于什么类别')
        a(f'  <p style="margin:0 0 6px;"><span style="{ss}">标签文字</span></p>')
        a(f'  <p style="font-size:13px;color:#4B5563;margin:0;line-height:1.7;text-align:justify;">说明文字</p>')
        a(f"")

    # ── 图片
    if "image" in c:
        cs = style_to_str(c["image"]["style"].get("container", {}))
        ims = style_to_str(c["image"]["style"].get("img", {}))
        a(f'  【图片】')
        a(f'  <section style="{cs}">')
        a(f'    <img src="图片路径" alt="描述" style="max-width:100%;height:auto;{ims}" />')
        a(f'  </section>')
        note = c["image"].get("note", "")
        if note:
            a(f'  ⚠️ {note}')
        a(f"")

    a(f"-->")
    return "\n".join(lines)


# ── 4. 生成预览 HTML ─────────────────────────────

def generate_preview(components: dict) -> str:
    """生成可视化预览 HTML，展示每个组件的实际渲染效果"""
    parts = [
        '<!DOCTYPE html><html><head><meta charset="utf-8">',
        '<title>样式提取预览</title>',
        '<style>body{margin:0;background:#f5f5f5;font-family:-apple-system,sans-serif}',
        '.preview-wrap{max-width:720px;margin:20px auto;background:#fff;padding:40px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08)}',
        '.comp-label{font-size:11px;color:#999;text-transform:uppercase;letter-spacing:2px;margin:32px 0 8px;padding-top:16px;border-top:1px solid #eee}',
        '.comp-label:first-child{border-top:none;margin-top:0}',
        '</style></head><body><div class="preview-wrap">',
        '<h1 style="font-size:20px;color:#333;margin:0 0 8px;">提取样式预览</h1>',
        '<p style="font-size:13px;color:#999;margin:0 0 24px;">自动从公众号文章 HTML 提取的组件样式</p>',
    ]

    c = components
    article_type = c.get("_meta", {}).get("article_type", "section")

    # ── textstyle / xiumi 型文章预览 ──
    if article_type in ("textstyle", "xiumi"):
        # 段落基础
        if "paragraph" in c:
            ps = style_to_str(c["paragraph"]["style"])
            parts.append(f'<p class="comp-label">段落</p>')
            parts.append(f'<p style="{ps}">段落样式示例文字，左右留白效果。</p>')

        if "body_base" in c:
            bs = style_to_str(c["body_base"]["style"])
            parts.append(f'<p class="comp-label">正文基础字体</p>')
            parts.append(f'<p><span style="{bs}">正文字体样式示例，font-size/line-height/letter-spacing。</span></p>')

        if "body_text" in c:
            s = style_to_str(c["body_text"]["style"])
            parts.append(f'<p class="comp-label">正文文字</p>')
            parts.append(f'<p style="margin:0 32px 16px;"><span style="{s}">{c["body_text"].get("sample","示例正文")} (x{c["body_text"].get("count",0)})</span></p>')

        # 色系色块
        if "color_palette" in c:
            palette = c["color_palette"].get("palette", [])
            parts.append(f'<p class="comp-label">色系</p>')
            parts.append(f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px;">')
            for p in palette:
                color = p["color"]
                role = p["role"]
                cnt = p["count"]
                parts.append(
                    f'<div style="width:60px;height:60px;background-color:{color};'
                    f'border-radius:6px;border:1px solid #eee;display:flex;align-items:flex-end;'
                    f'justify-content:center;padding:4px;">'
                    f'<span style="font-size:9px;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,0.5);">'
                    f'{role} x{cnt}</span></div>')
            parts.append(f'</div>')

        # 所有色块标签 + 强调 + 爆炸标题 + 卡片
        skip_keys = {"_meta", "container", "image", "paragraph", "body_base", "body_text", "color_palette"}
        for key, comp in c.items():
            if key in skip_keys:
                continue
            s = comp.get("style", {})
            if not s:
                continue
            ss = style_to_str(s)
            desc = comp.get("description", key)
            sample = comp.get("sample", "示例")
            count = comp.get("count", 0)

            # 卡片/色块用 div 展示，其他用 span
            if key.startswith("card_"):
                parts.append(f'<p class="comp-label">{desc} (x{count})</p>')
                parts.append(f'<div style="{ss};padding:12px 16px;border-radius:6px;margin:0 0 16px;">'
                             f'<span style="font-size:13px;color:#333;">{sample or "卡片内容"}</span></div>')
            else:
                parts.append(f'<p class="comp-label">{desc} (x{count})</p>')
                parts.append(f'<p style="margin:0 32px 16px;line-height:2;">'
                             f'<span style="{ss}">&nbsp;{sample}&nbsp;</span></p>')

        # 图片
        if "image" in c:
            parts.append(f'<p class="comp-label">图片</p>')
            cs = style_to_str(c["image"]["style"].get("container", {}))
            fs = style_to_str(c["image"]["style"].get("frame", {}))
            ims = style_to_str(c["image"]["style"].get("img", {}))
            img_html = (f'<img src="https://placehold.co/600x300/f0f0f0/999?text=示例图片" '
                        f'style="display:block;max-width:100%;height:auto;{ims}" />')
            if fs:
                parts.append(f'<section style="{fs}">'
                             f'<section style="{cs}">{img_html}</section></section>')
            else:
                parts.append(f'<section style="{cs}">{img_html}</section>')

        parts.append('</div></body></html>')
        return "\n".join(parts)

    # ── section 嵌套型文章预览 ──

    # 容器 info
    if "container" in c:
        s = c["container"]["style"]
        parts.append(f'<p class="comp-label">容器</p>')
        parts.append(f'<p style="font-size:12px;color:#666;">max-width: {s.get("max-width","?")}, '
                     f'font: {s.get("font-family","?")[:40]}..., '
                     f'color: {s.get("color","?")}, '
                     f'line-height: {s.get("line-height","?")}</p>')

    # 正文
    if "body_text" in c:
        s = c["body_text"]["style"]
        style_str = style_to_str(s)
        parts.append(f'<p class="comp-label">正文段落</p>')
        parts.append(f'<p style="{style_str}">先看实际视频，这是《错位时空：送信者》，'
                     f'一款治愈系解谜游戏。你扮演一个现代送信人，在海边长椅前打开时间窗。</p>')

    # 三种强调
    if "emphasis_bold_color" in c:
        s = style_to_str(c["emphasis_bold_color"]["style"])
        parts.append(f'<p class="comp-label">强调① 彩色加粗</p>')
        parts.append(f'<p style="font-size:14px;line-height:1.9;">这是一个<strong style="{s}">非常完整的商业游戏</strong>，用到了多种技术。</p>')

    if "emphasis_highlight" in c:
        s = style_to_str(c["emphasis_highlight"]["style"])
        parts.append(f'<p class="comp-label">强调② 渐变底色高亮</p>')
        parts.append(f'<p style="font-size:14px;line-height:1.9;">迟到<span style="{s}">几十年</span>的家书终于送到。</p>')

    if "emphasis_underline" in c:
        s = style_to_str(c["emphasis_underline"]["style"])
        parts.append(f'<p class="comp-label">强调③ 下划线</p>')
        parts.append(f'<p style="font-size:14px;line-height:1.9;">借助<span style="{s}">多智能体协作</span>平台完成。</p>')

    # 分节标题
    if "part_heading" in c:
        ph = c["part_heading"]
        cs = style_to_str(ph["style"])
        ns = style_to_str(ph["sub_styles"]["number"])
        ts = style_to_str(ph["sub_styles"]["title"])
        es = style_to_str(ph["sub_styles"]["english"])
        sep = ph["sub_styles"]["separator"]
        sep_s = style_to_str(sep)
        parts.append(f'<p class="comp-label">分节大数字标题</p>')
        parts.append(f'''<section style="{cs}">
  <section style="text-align:center;flex-shrink:0;">
    <p style="{ns}">01</p>
    <p style="margin:0;font-size:8px;font-weight:700;color:#D1D5DB;letter-spacing:2px;">PART</p>
  </section>
  <span style="{sep_s};flex-shrink:0;display:inline-block;"></span>
  <section>
    <p style="{ts}">灵感 · 从抖音到游戏</p>
    <p style="{es}">INSPIRATION</p>
  </section>
</section>''')

    # 小标题
    if "sub_heading_h4" in c:
        desc = c["sub_heading_h4"]["description"]
        s = style_to_str(c["sub_heading_h4"]["style"])
        sample = c["sub_heading_h4"].get("sample", "聊出世界观")
        parts.append(f'<p class="comp-label">{desc}</p>')
        parts.append(f'<h4 style="{s}">{sample}</h4>')

    if "sub_heading_highlight" in c:
        ps = style_to_str(c["sub_heading_highlight"]["style"]["p"])
        ss = style_to_str(c["sub_heading_highlight"]["style"]["span"])
        parts.append(f'<p class="comp-label">小标题（黄底渐变标注式）</p>')
        parts.append(f'<p style="{ps}"><span style="{ss}">第一层：时间窗</span></p>')

    # 步骤标签 + h4 组合（如原文 STEP 01 + 小标题）
    if "tag_step" in c and "sub_heading_h4" in c:
        tag_s = style_to_str(c["tag_step"]["style"])
        h4_s = style_to_str(c["sub_heading_h4"]["style"])
        parts.append(f'<p class="comp-label">步骤标签 + 小标题组合</p>')
        parts.append(f'<section style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                     f'<span style="{tag_s}">STEP 01</span>'
                     f'<h4 style="{h4_s}">聊出世界观</h4></section>')

    # 标签胶囊
    if "tag_capsule" in c:
        s = style_to_str(c["tag_capsule"]["style"])
        sample = c["tag_capsule"].get("sample", "标签")
        parts.append(f'<p class="comp-label">内容标签胶囊</p>')
        parts.append(f'<p style="margin:0 0 6px;"><span style="{s}">{sample}</span></p>'
                     f'<p style="font-size:13px;color:#4B5563;margin:0;line-height:1.7;">'
                     f'你跟古代的老周聊过"送信人规矩"，他会记住。</p>')

    # 步骤标签单独展示
    if "tag_step" in c:
        s = style_to_str(c["tag_step"]["style"])
        parts.append(f'<p class="comp-label">步骤标签（深色底）</p>')
        parts.append(f'<span style="{s}">STEP 01</span>')

    # 内容区 padding
    if "content_padding" in c:
        pad = c["content_padding"]["style"]["padding"]
        count = c["content_padding"].get("sample", "")
        parts.append(f'<p class="comp-label">内容区 padding</p>')
        parts.append(f'<p style="font-size:12px;color:#666;">padding: {pad}（{count}）</p>')

    # 图片
    if "image" in c:
        parts.append(f'<p class="comp-label">图片</p>')
        cs = style_to_str(c["image"]["style"].get("container", {}))
        fs = style_to_str(c["image"]["style"].get("frame", {}))
        ims = style_to_str(c["image"]["style"].get("img", {}))
        img_base = "display:block;max-width:100%;height:auto;"
        img_html = (f'<img src="https://placehold.co/600x300/f0f0f0/999?text=示例图片" '
                    f'style="{img_base}{ims}" />')
        if fs:
            parts.append(f'<section style="{fs}">'
                         f'<section style="{cs}">{img_html}</section></section>')
        else:
            parts.append(f'<section style="{cs}">{img_html}</section>')

    parts.append('</div></body></html>')
    return "\n".join(parts)


# ── 5. 对比报告 ─────────────────────────────────

def compare_with_template(components: dict) -> str:
    """与 wechat-green.html 模板的已知值对比"""
    template_values = {
        "container.max-width": "677px",
        "container.color": "rgb(58,58,58)",
        "container.line-height": "1.9",
        "container.font-size": "15px",
        "body_text.font-size": "15px",
        "body_text.line-height": "1.9",
        "body_text.color": "rgb(58,58,58)",
        "emphasis_bold_color.color": "#00a86b",
        "emphasis_highlight.background": "linear-gradient(120deg,#FDE68A 0%,rgba(255,255,255,0) 100%)",
        "emphasis_underline.border-bottom": "2px solid #A7F3D0",
        "part_heading.number.font-size": "28px",
        "part_heading.number.color": "#00a86b",
        "part_heading.title.font-size": "17px",
    }

    report = []
    report.append("=" * 60)
    report.append("对比报告：自动提取 vs wechat-green.html 模板")
    report.append("=" * 60)

    for key, expected in template_values.items():
        parts_k = key.split(".")
        comp_name = parts_k[0]
        if comp_name not in components:
            report.append(f"  ⚠️  {key}: 未提取到组件 '{comp_name}'")
            continue

        comp = components[comp_name]
        # 遍历到目标属性
        style = comp.get("style", {})
        if len(parts_k) == 2:
            actual = style.get(parts_k[1], "❌ 未提取")
        elif len(parts_k) == 3:
            sub = comp.get("sub_styles", {}).get(parts_k[1], {})
            actual = sub.get(parts_k[2], "❌ 未提取")
        else:
            actual = "?"

        match = "✅" if actual.strip() == expected.strip() else "⚠️"
        report.append(f"  {match} {key}")
        report.append(f"       模板: {expected}")
        report.append(f"       提取: {actual}")
        if match == "⚠️" and actual != "❌ 未提取":
            report.append(f"       → 差异可能是模板手动归一化的结果")

    return "\n".join(report)


# ── main ─────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法: python3 extract_styles.py <url_or_html_file>")
        print("例如: python3 extract_styles.py https://mp.weixin.qq.com/s/qGdmYj...")
        sys.exit(1)

    source = sys.argv[1]
    print(f"📥 读取: {source}")

    html = fetch_html(source)
    print(f"   HTML 大小: {len(html):,} 字符")

    content = extract_js_content(html)
    print(f"   js_content 大小: {len(content):,} 字符")

    extractor = StyleExtractor(content)
    components = extractor.extract_all()

    print(f"\n📦 提取到 {len(components)} 个组件:")
    for name, comp in components.items():
        print(f"   • {name}: {comp['description']}")

    # 样式名 → slug（用于文件名）
    theme = sys.argv[2] if len(sys.argv) > 2 else "自动提取"
    import unicodedata
    slug = re.sub(r'[^\w\-]', '-', theme).strip('-').lower() or "unnamed"

    # 输出目录: 项目 templates/ 或 /tmp/
    import os
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    templates_dir = os.path.join(proj_root, "templates")
    if os.path.isdir(templates_dir):
        out_dir = templates_dir
    else:
        out_dir = "/tmp"

    # 输出 JSON
    json_path = os.path.join(out_dir, f"{slug}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(components, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON 样式系统: {json_path}")

    # 生成预览
    preview_path = os.path.join(out_dir, f"{slug}-preview.html")
    preview_html = generate_preview(components)
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(preview_html)
    print(f"🖼  预览 HTML: {preview_path}")

    # 生成样式模板
    template_text = json_to_style_template(components, theme)
    template_path = os.path.join(out_dir, f"{slug}.html")
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(template_text)
    print(f"📋 样式模板: {template_path}")

    # 对比报告（仅对 qGdmYj 文章有效）
    report = compare_with_template(components)
    print(f"\n{report}")


if __name__ == "__main__":
    main()
