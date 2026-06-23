#!/usr/bin/env bun
/**
 * render-xshots.ts — Obsidian 笔记 → X 长文视觉风格 → 多张 3:4 小红书长截图
 *
 * 流程：
 *   1. 读 .md，剥 frontmatter，取标题（frontmatter.title > 首个 # H1 > 文件名）
 *   2. 解析 Obsidian 图片 ![[img.png]] 和标准 ![](path)，按 basename 在 vault 递归找 → file:// 绝对路径
 *   3. marked 把正文 md → HTML
 *   4. 填进 templates/x-longform.html（标题/正文 直接区域替换，banner 走 {{BANNER_URL}} 占位）
 *   5. playwright-core 加载 file://（复用已缓存 chromium），渲染宽 598
 *   6. 测全页高度，切成 N 张 1196×1595（≈3:4）PNG（末张补白）
 *
 * 用法：
 *   bun render-xshots.ts <note.md> [--banner <url|path>] [--out <dir>]
 *                        [--vault <dir>] [--width 598] [--dpr 2] [--keep-html]
 *
 * 输出：<out>/01.png 02.png ...，以及 <out>/_preview.html（--keep-html 时保留）
 * 依赖：bun、playwright-core、marked、已缓存的 ms-playwright chromium（或系统 Chrome）
 */
import { chromium } from "playwright-core";
import { marked } from "marked";
import {
  readFileSync, writeFileSync, mkdirSync, existsSync,
  readdirSync, statSync, rmSync,
} from "fs";
import { resolve, dirname, basename, join, extname, isAbsolute } from "path";
import { homedir } from "os";
import { pathToFileURL } from "url";

// ───────────────────────── 参数解析 ─────────────────────────
const argv = process.argv.slice(2);
if (argv.length === 0 || argv[0] === "-h" || argv[0] === "--help") {
  console.log(
    "用法: bun render-xshots.ts <note.md> [--banner <url|path>] [--out <dir>] " +
    "[--vault <dir>] [--width 598] [--dpr 2] [--keep-html]"
  );
  process.exit(argv.length === 0 ? 1 : 0);
}
const opts: Record<string, string | boolean> = {};
const positional: string[] = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--keep-html") opts.keepHtml = true;
  else if (a.startsWith("--")) { opts[a.slice(2)] = argv[++i]; }
  else positional.push(a);
}

const mdPath = resolve(positional[0]);
if (!existsSync(mdPath)) { console.error(`❌ 笔记不存在: ${mdPath}`); process.exit(1); }

const mdDir = dirname(mdPath);
const vault = (opts.vault as string) || process.env.OBSIDIAN_VAULT || "";
const outDir = resolve((opts.out as string) || join(mdDir, "xshots"));
const CSS_W = parseInt((opts.width as string) || "598", 10);
const DPR = parseFloat((opts.dpr as string) || "2");
const bannerArg = (opts.banner as string) || "";

const SCRIPT_DIR = dirname(Bun.fileURLToPath(import.meta.url));
const PROJ_DIR = resolve(SCRIPT_DIR, "..");
const TEMPLATE = join(PROJ_DIR, "templates", "x-longform.html");
if (!existsSync(TEMPLATE)) { console.error(`❌ 模板不存在: ${TEMPLATE}`); process.exit(1); }

// ───────────────────────── 工具函数 ─────────────────────────
const IMG_EXT = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]);

function htmlEscape(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** 递归索引一个目录下所有图片：basename(小写) -> 绝对路径（先到先得），跳过隐藏目录 */
function buildImageIndex(dir: string): Map<string, string> {
  const idx = new Map<string, string>();
  if (!dir || !existsSync(dir)) return idx;
  const walk = (d: string) => {
    let entries: string[];
    try { entries = readdirSync(d); } catch { return; }
    for (const name of entries) {
      if (name.startsWith(".")) continue;
      const full = join(d, name);
      let st;
      try { st = statSync(full); } catch { continue; }
      if (st.isDirectory()) walk(full);
      else if (IMG_EXT.has(extname(name).toLowerCase())) {
        const key = name.toLowerCase();
        if (!idx.has(key)) idx.set(key, full);
      }
    }
  };
  walk(dir);
  return idx;
}

let _vaultIndex: Map<string, string> | null = null;
function vaultIndex(): Map<string, string> {
  if (_vaultIndex === null) _vaultIndex = buildImageIndex(vault);
  return _vaultIndex;
}

const missingImages: string[] = [];
let fromVaultCount = 0;

/** 把一个图片引用（Obsidian 内部链接的 basename 或相对/绝对路径）解析成 file:// URL */
function resolveImage(ref: string): string | null {
  let r = ref.trim();
  if (/^(https?:|data:|file:)/i.test(r)) return r; // 已是可用 URL
  // Obsidian ![[name|size]] 里可能带 | 尺寸提示，去掉
  r = r.split("|")[0].trim();
  // 绝对路径
  if (isAbsolute(r) && existsSync(r)) return pathToFileURL(r).href;
  // 相对 md 目录
  const relToMd = resolve(mdDir, r);
  if (existsSync(relToMd)) return pathToFileURL(relToMd).href;
  // vault 里按 basename 递归找
  const hit = vaultIndex().get(basename(r).toLowerCase());
  if (hit) { fromVaultCount++; return pathToFileURL(hit).href; }
  missingImages.push(ref);
  return null;
}

// ───────────────────────── 解析 markdown ─────────────────────────
let raw = readFileSync(mdPath, "utf-8");

// 剥 YAML frontmatter，顺手抓 title
let frontTitle = "";
const fm = raw.match(/^---\n([\s\S]*?)\n---\n?/);
if (fm) {
  const t = fm[1].match(/^title:\s*["']?(.+?)["']?\s*$/m);
  if (t) frontTitle = t[1].trim();
  raw = raw.slice(fm[0].length);
}

// 取标题：frontmatter > 顶部 H1 > 文件名。
// 注意：只有当正文「顶部」就是 # 标题时才当文章标题并移除；
// 中段的 # 是正文小节标题，保留不动（否则会误删结构）。
raw = raw.replace(/^\s+/, ""); // 去掉开头空行，便于判断是否以 # 开头
let title = frontTitle;
const topH1 = raw.match(/^#\s+(.+?)\s*(?:\n|$)/);
if (topH1) {
  if (!title) title = topH1[1].trim();
  raw = raw.slice(topH1[0].length); // 仅移除顶部这一个 H1
}
if (!title) {
  // 文件名兜底：去掉末尾日期（如 " 26.06.22" / " 2026-06-22"）
  title = basename(mdPath, extname(mdPath))
    .replace(/\s*\d{2,4}[.\-]\d{1,2}[.\-]\d{1,2}\s*$/, "")
    .trim();
}

// 先把 Obsidian 内部图片链接 ![[img.png]] 转成标准 markdown ![](file://...)
raw = raw.replace(/!\[\[([^\]]+?)\]\]/g, (_m, inner) => {
  const url = resolveImage(inner);
  return url ? `![](${url})` : ""; // 找不到就丢掉这个嵌入
});

// marked 渲染；自定义 image 渲染器，解析标准 ![](src) 的本地路径
const renderer = new marked.Renderer();
const defaultImage = renderer.image.bind(renderer);
renderer.image = (token: any) => {
  const url = resolveImage(token.href || "");
  if (!url) return ""; // 找不到的图丢掉
  const alt = htmlEscape(token.text || "");
  return `<img src="${url}" alt="${alt}">`;
};
marked.setOptions({ renderer, breaks: false, gfm: true });
const bodyHtml = marked.parse(raw) as string;

// ───────────────────────── 填模板 ─────────────────────────
let tpl = readFileSync(TEMPLATE, "utf-8");

// 标题：替换 h1#article-title 内文
tpl = tpl.replace(
  /(<h1[^>]*id="article-title"[^>]*>)[\s\S]*?(<\/h1>)/,
  (_m, open, close) => open + htmlEscape(title) + close
);

// 正文：替换 div#article-body 内部（锚到其后的 <div class="article-end">）
tpl = tpl.replace(
  /(<div[^>]*id="article-body"[^>]*>)[\s\S]*?(<\/div>\s*<div class="article-end">)/,
  (_m, open, close) => open + "\n" + bodyHtml + "\n" + close
);

// banner：{{BANNER_URL}} 占位符替换成可用 URL（找不到则留空 → 显示占位框）
let bannerUrl = "";
if (bannerArg) bannerUrl = resolveImage(bannerArg) || "";
tpl = tpl.replace(/\{\{BANNER_URL\}\}/g, bannerUrl);

// ───────────────────────── 写出填好的 HTML ─────────────────────────
mkdirSync(outDir, { recursive: true });
const filledHtml = join(outDir, "_preview.html");
writeFileSync(filledHtml, tpl, "utf-8");

// ───────────────────────── 找 chromium ─────────────────────────
function findChromium(): string {
  const base = join(homedir(), "Library/Caches/ms-playwright");
  if (existsSync(base)) {
    for (const dir of readdirSync(base)) {
      if (!dir.startsWith("chromium-")) continue; // 跳过 headless_shell
      const appRoot = join(base, dir);
      // 找 *.app/Contents/MacOS/<exe>（排除 Helper）
      const stack = [appRoot];
      while (stack.length) {
        const d = stack.pop()!;
        let entries: string[];
        try { entries = readdirSync(d); } catch { continue; }
        for (const name of entries) {
          const full = join(d, name);
          let st; try { st = statSync(full); } catch { continue; }
          if (st.isDirectory()) { if (!name.includes("Helper")) stack.push(full); }
          else if (d.endsWith("Contents/MacOS") && !name.includes("Helper")) return full;
        }
      }
    }
  }
  const sys = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
  if (existsSync(sys)) return sys;
  throw new Error("找不到 chromium，也找不到系统 Chrome");
}

// ───────────────────────── 截图 + 切片 ─────────────────────────
const tileCssH = Math.round(CSS_W * 4 / 3); // 3:4 每片 CSS 高度（取整，避免小数 clip 越界）
const deviceW = Math.round(CSS_W * DPR);
const deviceTileH = Math.round(tileCssH * DPR);

const exe = findChromium();
const browser = await chromium.launch({ executablePath: exe, headless: true });
const page = await browser.newPage({
  viewport: { width: CSS_W, height: Math.ceil(tileCssH) },
  deviceScaleFactor: DPR,
});

await page.goto(pathToFileURL(filledHtml).href, { waitUntil: "load" });
// 等图片加载完（networkidle 对 file:// 也有效）
try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch {}
await page.evaluate(() => (document as any).fonts?.ready);

// 智能连续切（黑名单式）：默认每页正好切在 tileCssH 处，最大化填充、几乎无留白；
// 唯一约束是「不切半行字」——收集所有文字行的 [top,bottom] 作为禁区，
// 若切割线落进某行内部就上移到该行顶（把整行让到下一页，页底留白 < 一行）。
// 图片不设禁区，可像长截图一样自由拦腰切（上一张显示一部分、下一张接着显示）。
const { lines, contentBottom } = await page.evaluate(() => {
  const sy = () => window.scrollY;
  const lines: { t: number; b: number }[] = [];
  let maxB = 0;
  const TEXT = /^(P|LI|BLOCKQUOTE|H1|H2|H3|H4|H5|H6)$/;
  const bot = (el: Element) => el.getBoundingClientRect().bottom + sy();
  const hasImg = (el: Element) => el.tagName === "IMG" || !!el.querySelector("img");
  const addLines = (el: Element) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    for (const r of Array.from(range.getClientRects())) {
      if (r.height <= 0) continue;
      const t = r.top + sy(), b = r.bottom + sy();
      lines.push({ t, b });
      if (b > maxB) maxB = b;
    }
  };
  const walk = (el: Element) => {
    if (hasImg(el)) { const b = bot(el); if (b > maxB) maxB = b; return; } // 图不设禁区，可自由切
    if (TEXT.test(el.tagName)) { addLines(el); return; } // 文字逐行记禁区
    if (el.children.length) { for (const c of Array.from(el.children)) walk(c); }
    else { const b = bot(el); if (b > maxB) maxB = b; }
  };
  const ab = document.getElementById("article-body");
  const SKIP = /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/;
  for (const c of Array.from(document.body.children)) {
    if (c.classList.contains("article-end") || SKIP.test(c.tagName)) continue;
    if (c === ab) { if (ab) for (const cc of Array.from(ab.children)) walk(cc); }
    else walk(c);
  }
  return { lines, contentBottom: Math.round(maxB) };
});

// 贪心：每页目标切点 = 起点 + tileCssH；若落在某文字行内则上移到该行顶（不切半行）。
const cuts: number[] = [0];
let cur = 0, guard = 0;
while (cur < contentBottom - 1 && guard++ < 600) {
  let target = cur + tileCssH;
  if (target >= contentBottom) { cuts.push(contentBottom); break; }
  for (const ln of lines) {
    if (ln.t + 0.5 < target && target < ln.b - 0.5) { target = Math.floor(ln.t); break; }
  }
  if (target <= cur) target = cur + tileCssH; // 兜底：单行比整页还高时不后退
  cuts.push(target);
  cur = target;
}
const n = Math.max(1, cuts.length - 1);

// 撑高页面（末页底 + 余量）+ 加白色遮罩。视口设为一个 tile 大小，
// 逐页 scrollTo 后截「整个视口」（比 clip 在大 y 坐标更稳，不会报越界）。
await page.setViewportSize({ width: CSS_W, height: tileCssH });
await page.evaluate((minH) => {
  document.body.style.minHeight = minH + "px";
  const m = document.createElement("div");
  m.id = "__pagemask__";
  m.style.cssText = "position:absolute;left:0;right:0;background:#fff;z-index:99999;display:none";
  document.body.appendChild(m);
}, Math.ceil(cuts[n - 1] + tileCssH) + 50);

const files: string[] = [];
for (let i = 0; i < n; i++) {
  const startY = cuts[i];
  const contentEnd = cuts[i + 1] ?? contentBottom; // 本页内容底
  // 遮罩盖住 [contentEnd, startY+TILE] 让页底干净；滚到 startY 让视口正好对齐本页
  await page.evaluate(({ startY, maskTop, maskBottom }) => {
    const m = document.getElementById("__pagemask__")!;
    if (maskBottom > maskTop + 0.5) {
      m.style.top = maskTop + "px";
      m.style.height = (maskBottom - maskTop) + "px";
      m.style.display = "block";
    } else m.style.display = "none";
    window.scrollTo(0, startY);
  }, { startY, maskTop: contentEnd, maskBottom: startY + tileCssH });

  const num = String(i + 1).padStart(2, "0");
  const out = join(outDir, `${num}.png`);
  await page.screenshot({ path: out }); // 截整个视口 = 一个 3:4 tile
  files.push(out);
}

await browser.close();

// 末片若不想保留 preview html 就删
if (!opts.keepHtml) { try { rmSync(filledHtml); } catch {} }

// ───────────────────────── 汇总 ─────────────────────────
console.log(JSON.stringify({
  title,
  tiles: n,
  size: `${deviceW}x${deviceTileH}`,
  out: outDir,
  files: files.map((f) => basename(f)),
  fromVault: fromVaultCount,
  missing: missingImages,
}, null, 2));

console.error(`\n✅ ${n} 张 3:4 截图（${deviceW}×${deviceTileH}）→ ${outDir}`);
if (missingImages.length) {
  console.error(`⚠️  ${missingImages.length} 张图找不到（已跳过）：`);
  missingImages.forEach((m) => console.error(`   - ${m}`));
}
