from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import base64
import os
import random
import sys
import traceback
from urllib.parse import parse_qs, quote, unquote, urlparse

from ranker import is_hvac_query, rank_results, split_query
from search_engine import download_paper_pdfs, read_result_pages, search_papers, search_web
from summarizer import build_newsletter, source_summary


PAGE_STYLE = """
:root {
  --ink: #172033;
  --muted: #657083;
  --navy: #223a59;
  --navy-2: #344e72;
  --line: #dde4ee;
  --paper: #fbfaf7;
  --soft: #f4f6f9;
  --accent: #d84b42;
}
* { box-sizing: border-box; }
html {
  min-height: 100%;
  background: #f6f8fb;
}
body {
  margin: 0;
  font-family: "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;
  color: var(--ink);
  min-height: 100%;
  background:
    linear-gradient(180deg, rgba(246,248,251,.82), rgba(255,255,255,.93) 34%, rgba(255,255,255,.96)),
    var(--body-bg) center top / cover fixed no-repeat;
}
body:before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  background: rgba(255,255,255,.28);
  backdrop-filter: blur(1.5px) saturate(.92);
}
header {
  max-width: 1420px;
  margin: 22px auto 0;
  padding: 34px 34px 28px;
  color: white;
  background:
    linear-gradient(90deg, rgba(22,43,70,.84), rgba(29,58,91,.66), rgba(29,58,91,.32)),
    var(--header-bg) center 46% / cover no-repeat;
  border-radius: 8px;
  box-shadow: 0 18px 40px rgba(34, 58, 89, .18);
}
header .eyebrow { letter-spacing: .16em; font-size: 12px; color: #d8e5f5; }
header h1 { margin: 8px 0 10px; font-size: 30px; }
header p { max-width: 1080px; line-height: 1.7; margin: 0; color: #eaf1fb; }
main { max-width: 1420px; margin: 0 auto; padding: 22px 18px 42px; }
.tabs { display: flex; gap: 10px; margin: 6px 0 22px; border-bottom: 1px solid var(--line); }
.tab { padding: 10px 18px; border: 1px solid var(--line); border-bottom: 0; border-radius: 22px 22px 0 0; background: white; color: var(--muted); text-decoration: none; }
.tab.active { background: var(--navy); color: white; }
.layout { display: grid; grid-template-columns: 315px 1fr; gap: 22px; align-items: start; }
.compare-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.compare-pane section { padding: 18px; }
.compare-pane .report { padding: 22px; font-size: 14px; }
.compare-pane .report h2 { font-size: 22px; }
.compare-pane .report h3 { font-size: 17px; }
.compare-pane h2 { font-size: 21px; }
.compare-pane h3 { font-size: 16px; }
.compare-pane .metrics { grid-template-columns: repeat(2, 1fr); }
.compare-pane .metric { min-height: 74px; padding: 12px; }
.compare-pane .metric b { font-size: 18px; }
.compare-title { margin: 0 0 12px; font-size: 22px; }
section, aside {
  background: rgba(255,255,255,.94);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(23, 32, 51, .06);
  backdrop-filter: blur(8px);
}
aside { padding: 18px; position: sticky; top: 16px; }
section { padding: 22px; margin-bottom: 18px; }
h2 { margin: 0 0 16px; font-size: 24px; }
h3 { margin: 0 0 10px; font-size: 18px; }
label { display: block; margin: 12px 0 6px; font-weight: 700; }
.hint { margin: 4px 0 10px; font-size: 13px; color: var(--muted); line-height: 1.55; }
.method-note { color: var(--muted); font-size: 13px; line-height: 1.7; }
input {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #c8d3e2;
  border-radius: 6px;
  background: #fff;
  font-size: 15px;
}
.check-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 6px;
  font-weight: 700;
}
.check-row input { width: auto; }
.compare-query { display: none; }
form.compare-on .compare-query { display: block; }
.download-box {
  margin: 12px 0 16px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(244,246,249,.78);
}
.download-link {
  display: inline-block;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--navy);
  color: white;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
}
select {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #c8d3e2;
  border-radius: 6px;
  background: #fff;
  font-size: 15px;
}
button {
  width: 100%;
  margin-top: 14px;
  padding: 12px 16px;
  border: 0;
  border-radius: 6px;
  background: var(--navy);
  color: white;
  font-weight: 700;
  cursor: pointer;
}
.quick a {
  display: inline-block;
  margin: 5px 5px 0 0;
  padding: 6px 10px;
  border-radius: 20px;
  border: 1px solid var(--line);
  color: var(--navy);
  text-decoration: none;
  font-size: 13px;
}
.metrics { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.metric { padding: 14px; background: var(--soft); border-radius: 8px; min-height: 86px; }
.metric span { color: var(--muted); font-size: 13px; }
.metric b { display: block; font-size: 22px; margin-top: 8px; line-height: 1.2; }
.report {
  background: rgba(251,250,247,.96);
  border-color: #ece7dc;
  padding: 28px 34px;
  line-height: 1.72;
  font-size: 16px;
}
.report h2 { font-size: 26px; border-bottom: 1px solid #e2ddd2; padding-bottom: 14px; }
.report h3 { font-size: 20px; margin-top: 22px; }
.report-emphasis {
  font-size: 18px;
  line-height: 1.75;
  color: #10223c;
  margin: 18px 0;
}
.source-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.result, .paper {
  border-top: 1px solid var(--line);
  padding: 14px 0;
}
.source-bullet {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.source-bullet img {
  width: 28px;
  height: 28px;
  object-fit: contain;
  flex: 0 0 auto;
  filter: drop-shadow(0 4px 8px rgba(23,32,51,.12));
}
.source-card {
  margin: 12px 0;
  padding: 10px 12px;
  border-left: 3px solid rgba(34,58,89,.18);
  background: rgba(255,255,255,.56);
  border-radius: 8px;
}
.source-card p { margin: 4px 0; }
.source-detail {
  margin-left: 38px !important;
  color: var(--muted);
  line-height: 1.68;
}
.source-note {
  color: var(--muted);
  font-size: 13px;
  margin-top: 6px;
}
.summary-label {
  display: inline-block;
  margin: 4px 0 6px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef4fb;
  color: var(--navy);
  font-size: 12px;
}
.source-summary {
  margin: 0 0 8px;
  line-height: 1.75;
}
.result:first-child, .paper:first-child { border-top: 0; }
.source-title { margin-bottom: 4px; }
.source-domain { color: var(--muted); font-size: 13px; margin: 0 0 8px; }
.url { color: #1769aa; word-break: break-all; }
.meta { color: var(--muted); font-size: 13px; }
.score { color: var(--accent); font-weight: 800; }
pre { white-space: pre-wrap; line-height: 1.65; background: #f7fafc; border-radius: 8px; padding: 14px; }
code { background: #eef4fb; padding: 2px 5px; border-radius: 4px; }
.loading {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(246, 248, 252, .88);
  backdrop-filter: blur(5px);
  align-items: center;
  justify-content: center;
}
.loading-card {
  width: min(420px, 86vw);
  background: white;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 26px;
  box-shadow: 0 24px 60px rgba(23, 32, 51, .18);
  text-align: center;
}
.mascot {
  width: 88px;
  height: 88px;
  margin: 0 auto 12px;
  object-fit: contain;
  filter: drop-shadow(0 14px 18px rgba(34, 58, 89, .18));
  animation: hop 1.05s ease-in-out infinite;
}
.progress {
  height: 8px;
  overflow: hidden;
  border-radius: 99px;
  background: #eef3f9;
  margin-top: 16px;
}
.progress span {
  display: block;
  width: 42%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #77c7f2, #223a59);
  animation: loading 1.45s ease-in-out infinite;
}
@keyframes hop {
  0%, 100% { transform: translateY(0) scale(1, 1); }
  45% { transform: translateY(-18px) scale(.96, 1.04); }
  65% { transform: translateY(0) scale(1.08, .92); }
}
@keyframes loading {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(245%); }
}
.status-hero {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}
.status-hero img {
  width: 54px;
  height: 54px;
  object-fit: contain;
}
.status-hero p { margin: 3px 0 0; color: var(--muted); }
.empty-state {
  text-align: center;
  padding: 34px 24px;
}
.empty-state img {
  width: 76px;
  height: 76px;
  object-fit: contain;
}
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .compare-layout { grid-template-columns: 1fr; }
  aside { position: static; }
  .metrics, .source-grid { grid-template-columns: 1fr; }
}
"""


def base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def log_error(message: str) -> None:
    if os.environ.get("HVAC_AGENT_LOG") != "1":
        return
    try:
        with (runtime_dir() / "HVAC检索智能体运行日志.txt").open("a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


def run_pipeline(query: str, search_top_n: int, read_top_k: int, channel: str, paper_top_n: int = 6):
    search_top_n = max(5, min(search_top_n, 40))
    read_top_k = max(1, min(read_top_k, 15, search_top_n))
    paper_top_n = max(2, min(paper_top_n, 12))
    raw_results, search_engine = search_web(query, search_top_n, channel)
    paper_results, paper_engine = search_papers(query, paper_top_n)
    combined = raw_results + paper_results
    candidate_results = rank_results(combined, query)[:search_top_n]
    for idx, result in enumerate(candidate_results, start=1):
        result.rank = idx
    read_result_pages(candidate_results, read_top_k)
    kept_results = rank_results(candidate_results, query)[:search_top_n]
    for idx, result in enumerate(kept_results, start=1):
        result.rank = idx
    read_success_count = sum(1 for r in kept_results if r.read_success)
    newsletter = build_newsletter(
        query=query,
        search_engine=f"{search_engine} + {paper_engine}",
        raw_count=len(kept_results),
        read_success_count=read_success_count,
        kept_results=kept_results,
    )
    shown_papers = [r for r in paper_results if any(r.url == kept.url for kept in kept_results)]
    if not shown_papers:
        shown_papers = paper_results[: min(len(paper_results), search_top_n)]
    return candidate_results, kept_results, shown_papers, f"{search_engine} + {paper_engine}", read_success_count, newsletter


def rock_files() -> list[str]:
    folder = base_dir() / "洛克"
    files = sorted(p.name for p in folder.glob("*.webp"))
    return files or ["juhuali.webp"]


def bg_background_name() -> str:
    embedded = base_dir() / "背景" / "embedded" / "body_bg.webp"
    if embedded.exists():
        return "embedded/body_bg.webp"
    folder = base_dir() / "背景"
    images = [p for p in folder.glob("*") if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    if not images:
        return ""
    return max(images, key=lambda p: p.stat().st_size).name


def bg_header_name() -> str:
    embedded = base_dir() / "背景" / "embedded" / "header_bg.webp"
    if embedded.exists():
        return "embedded/header_bg.webp"
    folder = base_dir() / "背景"
    preferred = folder / "背景1.png"
    if preferred.exists():
        return preferred.name
    return bg_background_name()


def source_icon_files() -> list[str]:
    folder = base_dir() / "背景" / "icons_clean"
    files = sorted(p.name for p in folder.glob("*.png"))
    return files


def asset_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/webp" if suffix == ".webp" else "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def bg_data_uri(name: str) -> str:
    return asset_data_uri(base_dir() / "背景" / name)


def rock_data_uris(limit: int = 16) -> list[str]:
    folder = base_dir() / "洛克"
    files = rock_files()
    preferred = [name for name in ["juhuali.webp", "dimo.webp", "luoyin.webp"] if name in files]
    rest = [name for name in files if name not in preferred]
    if len(files) > limit:
        files = preferred + random.sample(rest, max(0, limit - len(preferred)))
    return [asset_data_uri(folder / name) for name in files]


def random_source_icon_url() -> str:
    files = source_icon_files()
    if not files:
        return ""
    return asset_data_uri(base_dir() / "背景" / "icons_clean" / random.choice(files))


def random_rock_url() -> str:
    folder = base_dir() / "洛克"
    return asset_data_uri(folder / random.choice(rock_files()))


def render_form(query="热泵节能", search_top_n=20, read_top_k=5, channel="domestic", compare=False, query2="HVAC智能控制", paper_top_n=6):
    examples = ["热泵节能", "HVAC智能控制", "变风量空调系统节能", "楼宇自控 HVAC 节能"]
    quick = " ".join(
        f"<a onclick='showLoading()' href='/?q={quote(item)}&n={search_top_n}&k={read_top_k}&p={paper_top_n}&channel={channel}'>{escape(item)}</a>"
        for item in examples
    )
    domestic_selected = "selected" if channel == "domestic" else ""
    international_selected = "selected" if channel == "international" else ""
    checked = "checked" if compare else ""
    form_class = "compare-on" if compare else ""
    return f"""
<aside>
  <h2>检索配置</h2>
  <form method="get" action="/" class="{form_class}">
    <label>查询关键词 A</label>
    <input name="q" value="{escape(query)}" placeholder="例如：热泵节能、HVAC智能控制">
    <p class="hint">输入 HVAC 系统节能方向，例如热泵、智能控制、变风量系统、楼宇自控。</p>

    <label class="check-row"><input name="compare" value="1" type="checkbox" {checked} onchange="this.form.classList.toggle('compare-on', this.checked)"> 启用双关键词对比</label>
    <div class="compare-query">
      <label>查询关键词 B</label>
      <input name="q2" value="{escape(query2)}" placeholder="例如：楼宇自控 HVAC 节能">
      <p class="hint">勾选后会同时检索两个主题，右侧分栏展示，方便比较资料来源和结论差异。</p>
    </div>

    <label>检索渠道</label>
    <select name="channel">
      <option value="domestic" {domestic_selected}>国内渠道</option>
      <option value="international" {international_selected}>国际化渠道（需科学上网）</option>
    </select>
    <p class="hint">国内渠道更稳定；国际化渠道更适合补充英文网页和论文线索。</p>

    <label>搜索结果数量</label>
    <input name="n" type="number" min="5" max="40" value="{search_top_n}">
    <p class="hint">控制检索覆盖面，对应 search_top_n。数值越大，资料更多，等待时间也更长。</p>

    <label>正文读取条数</label>
    <input name="k" type="number" min="1" max="15" value="{read_top_k}">
    <p class="hint">控制最多打开前多少条搜索结果读取正文，对应 read_top_k；不是多层爬取。建议先用 3-5。</p>

    <label>论文线索数量</label>
    <input name="p" type="number" min="2" max="12" value="{paper_top_n}">
    <p class="hint">控制论文线索区最多整理多少条公开论文线索。能否下载 PDF 取决于论文页面是否公开提供文件。</p>

    <button type="submit">开始联网检索</button>
  </form>
  <div class="quick"><p class="hint">快速示例：</p>{quick}</div>
</aside>
"""


def markdown_to_html(text: str) -> str:
    lines = []
    section_heads = ("研究主题：", "主题归类：", "资料概况：")
    emphasis_heads = ("针对问题的回答：", "需核对信息：", "下一步整理方向：")
    in_sources = False
    for line in text.splitlines():
        clean = line.strip()
        if clean.startswith("### "):
            lines.append(f"<h2>{escape(clean[4:])}</h2>")
        elif clean == "HVAC 系统节能技术检索小报":
            lines.append(f"<h2>{escape(clean)}</h2>")
        elif clean == "核心发现":
            in_sources = False
            lines.append(f"<h3>{escape(clean)}</h3>")
        elif clean == "重要来源":
            in_sources = True
            lines.append(f"<h3>{escape(clean)}</h3>")
        elif clean.startswith(section_heads):
            in_sources = False
            lines.append(f"<h3>{escape(clean)}</h3>")
        elif clean.startswith(emphasis_heads):
            in_sources = False
            lines.append(f"<p class='report-emphasis'>{escape(clean)}</p>")
        elif clean.startswith("**") and clean.endswith("**"):
            lines.append(f"<h3>{escape(clean.replace('**', ''))}</h3>")
        elif clean.startswith("**") and "：" in clean:
            lines.append(f"<h3>{escape(clean.replace('**', ''))}</h3>")
        elif clean.startswith("- "):
            if in_sources:
                icon = random_source_icon_url()
                icon_html = f"<img src='{escape(icon)}' alt='来源'>" if icon else ""
                lines.append(f"<div class='source-card'><p class='source-bullet'>{icon_html}<span>{escape(clean[2:])}</span></p>")
            else:
                lines.append(f"<p>• {escape(clean[2:])}</p>")
        elif in_sources and clean.startswith(("来源：", "搜索页摘要：", "正文摘录：", "说明：")):
            lines.append(f"<p class='source-detail'>{escape(clean)}</p>")
            if clean.startswith(("搜索页摘要：", "正文摘录：")):
                lines.append("</div>")
            elif clean.startswith("说明："):
                lines.append("</div>")
        elif clean:
            in_sources = False
            lines.append(f"<p>{escape(clean)}</p>")
    return "\n".join(lines)


def render_results(results, class_name="result"):
    rows = []
    for idx, r in enumerate(results, start=1):
        shown_rank = idx if class_name == "paper" else (r.rank or idx)
        image_html = f"<p class='meta'>页面图片线索：<a href='{escape(r.image_url)}' target='_blank'>{escape(r.image_url)}</a></p>" if r.image_url else ""
        source_type_html = ""
        if r.source_type and r.source_type != "未知":
            source_type_html = f" 来源类型：<code>{escape(r.source_type)}</code>"
        failure_html = f"<p class='meta'>读取说明：{escape(r.read_error)}</p>" if r.read_error else ""
        summary = source_summary(r, 520)
        summary_label = "正文摘录" if r.read_success and r.content else "搜索页摘要"
        summary_html = (
            f"<p class='summary-label'>{summary_label}</p><p class='source-summary'>{escape(summary)}</p>"
            if summary
            else (
                "<p class='source-note'>页面已打开，但没有提取到可用摘要，建议打开原文核对。</p>"
                if r.read_success
                else "<p class='source-note'>该来源只提供题名或元数据，建议打开原文核对。</p>"
            )
        )
        rows.append(
            f"""
<div class="{class_name}">
  <h3 class="source-title">{shown_rank}. <a href="{escape(r.url)}" target="_blank">{escape(r.title)}</a></h3>
  <p class="source-domain">{escape(r.domain)}{source_type_html}</p>
  {summary_html}
  {image_html}
  <p class="meta">域名：<code>{escape(r.domain)}</code>{source_type_html}
  相关性分数：<span class="score">{r.score}</span> 正文读取：{"完成" if r.read_success else "未完成"}</p>
  <p class="meta">命中依据：{escape("；".join(r.matched_terms))}</p>
  {failure_html}
</div>
"""
        )
    return "\n".join(rows) if rows else "<p class='hint'>暂无结果。</p>"


def render_metrics(query: str, raw, kept, read_count: int, channel: str) -> str:
    channel_label = "国际化渠道" if channel == "international" else "国内渠道"
    metrics = [
        ("研究主题", query),
        ("候选资料", len(raw)),
        ("正文读取成功", read_count),
        ("展示资料", len(kept)),
        ("检索渠道", channel_label),
    ]
    rows = [
        f"<div class='metric'><span>{escape(str(name))}</span><b>{escape(str(value))}</b></div>"
        for name, value in metrics
    ]
    return "<div class='metrics'>" + "".join(rows) + "</div>"


def download_link_html(query: str, search_top_n: int, read_top_k: int, paper_top_n: int, channel: str) -> str:
    href = (
        f"/download_papers?q={quote(query)}&n={search_top_n}"
        f"&k={read_top_k}&p={paper_top_n}&channel={quote(channel)}"
    )
    return (
        "<div class='download-box'>"
        "<p class='method-note'>可尝试把论文线索中能直接访问到的 PDF 保存到本地。只做单跳下载，不做站点批量爬取。</p>"
        f"<a class='download-link' onclick='showLoading()' href='{href}'>一键导出可下载 PDF</a>"
        "</div>"
    )


def render_search_block(query: str, search_top_n: int, read_top_k: int, paper_top_n: int, channel: str, compact: bool = False) -> str:
    if not is_hvac_query(query):
        return f"<section class='empty-state'><img src='{random_rock_url()}' alt='主题不相关'><h2>这个主题暂不在 HVAC 系统节能范围内</h2><p class='hint'>请换成暖通、空调、热泵、楼宇自控、建筑能源、通风、制冷、变风量等相关方向。</p></section>"
    raw, kept, papers, engine, read_count, newsletter = run_pipeline(query, search_top_n, read_top_k, channel, paper_top_n)
    if not kept:
        return f"<section class='empty-state'><img src='{random_rock_url()}' alt='未找到相关资料'><h2>没有找到足够相关的 HVAC 资料</h2><p class='hint'>可以换一个更具体的表达，例如“楼宇自控 HVAC”“变风量空调系统节能”“热泵供热能效”。</p></section>"
    parts = [
        f"<section><div class='status-hero'><img src='{random_rock_url()}' alt='检索完成'><div><h2>检索完成</h2><p>已完成资料整理，可继续查看小报、论文线索和原始来源。</p></div></div>{render_metrics(query, raw, kept, read_count, channel)}</section>",
        f"<section class='report'>{markdown_to_html(newsletter)}</section>",
        f"<section><h2>论文线索区</h2><p class='method-note'>优先整理 ScienceDirect、Crossref、arXiv 等公开题名、链接和摘要线索；当前最多整理 {paper_top_n} 条；仅访问检索结果指向的页面。</p>{download_link_html(query, search_top_n, read_top_k, paper_top_n, channel)}{render_results(papers, 'paper')}</section>",
        f"<section><h2>搜索结果区</h2>{render_results(kept)}</section>",
    ]
    return "\n".join(parts)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        log_error("HTTP " + (format % args))

    def do_GET(self):
        try:
            self._do_GET()
        except Exception:
            error = traceback.format_exc()
            log_error(error)
            body = f"<h1>应用内部错误</h1><pre>{escape(error)}</pre>".encode("utf-8", errors="ignore")
            try:
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                pass

    def _do_GET(self):
        if urlparse(self.path).path == "/download_papers":
            self.serve_paper_download()
            return
        if urlparse(self.path).path == "/favicon.ico":
            self.serve_favicon()
            return
        if self.path.startswith("/rock/"):
            self.serve_rock_asset()
            return
        if self.path.startswith("/bg/"):
            self.serve_bg_asset()
            return
        params = parse_qs(urlparse(self.path).query, encoding="utf-8", errors="ignore")
        query = params.get("q", [""])[0] or ""
        query2 = params.get("q2", [""])[0] or ""
        compare = params.get("compare", [""])[0] == "1"
        search_top_n = int(params.get("n", ["20"])[0])
        read_top_k = int(params.get("k", ["5"])[0])
        paper_top_n = int(params.get("p", ["6"])[0])
        channel = params.get("channel", ["domestic"])[0]

        html = [
            "<!doctype html><html><head><meta charset='utf-8'>",
            "<title>HVAC 系统节能技术检索智能体</title>",
            "<link rel='icon' href='/favicon.ico' sizes='any'>",
            f"<style>:root{{--body-bg:url('{bg_data_uri(bg_background_name())}');--header-bg:url('{bg_data_uri(bg_header_name())}');}}{PAGE_STYLE}</style></head><body>",
            "<script>",
            "const ROCK_ICONS = [" + ",".join("'" + uri + "'" for uri in rock_data_uris()) + "];",
            "function randIcon(){return ROCK_ICONS[Math.floor(Math.random()*ROCK_ICONS.length)];}",
            "function showLoading(){const box=document.querySelector('.loading'); box.style.display='flex'; const texts=['菊花梨挖资料中','在网页里摸鱼中','给来源排队中','正文摸索中','小报整理中','翻论文标题中','给网页排座位中','摘摘要中','查找靠谱来源中','给热泵做体检中','冷却塔旁边蹲点中','和楼控系统对暗号中','把广告页赶出去中','给关键词洗澡中','整理证据链中','马上出小报中']; const el=document.querySelector('.loading-text'); const img=document.querySelector('.loading .mascot'); function pick(){el.textContent=texts[Math.floor(Math.random()*texts.length)]; img.src=randIcon();} pick(); setInterval(pick,900);}",
            "</script>",
            f"<div class='loading'><div class='loading-card'><img class='mascot' src='{random_rock_url()}' alt='检索中'><h3 class='loading-text'>资料翻找中</h3><p class='hint'>正在检索、读取正文并整理小报。</p><div class='progress'><span></span></div></div></div>",
            "<header><div class='eyebrow'>HVAC RESEARCH ASSISTANT</div><h1>HVAC 系统节能技术检索智能体</h1><p>面向暖通空调节能技术调研，整合联网资料、论文线索、来源信息与技术小报，帮助快速形成可核验的主题综述。</p></header>",
            "<main><div class='tabs'><a class='tab active' href='#report'>研究小报</a><a class='tab' href='#papers'>论文线索</a><a class='tab' href='#results'>搜索结果</a></div>",
            "<div class='layout'>",
            render_form(query or "热泵节能", search_top_n, read_top_k, channel, compare, query2 or "HVAC智能控制", paper_top_n),
            "<div>",
        ]

        if query:
            try:
                if compare and query2.strip():
                    html.append("<div class='compare-layout'>")
                    html.append(f"<div class='compare-pane'><h2 class='compare-title'>A：{escape(query)}</h2>{render_search_block(query, search_top_n, read_top_k, paper_top_n, channel, True)}</div>")
                    html.append(f"<div class='compare-pane'><h2 class='compare-title'>B：{escape(query2)}</h2>{render_search_block(query2, search_top_n, read_top_k, paper_top_n, channel, True)}</div>")
                    html.append("</div>")
                else:
                    html.append(render_search_block(query, search_top_n, read_top_k, paper_top_n, channel))
            except Exception as exc:
                html.append(f"<section><div class='status-hero'><img src='{random_rock_url()}' alt='检索未完成'><div><h2>检索未完成</h2><p>当前搜索源响应不稳定，可以降低搜索结果数量或正文读取条数后重试。</p></div></div></section>")
        else:
            html.append("<section class='report'><h2>学术提要</h2><p>请从左侧输入 HVAC 系统节能方向。</p></section>")

        html.append("</div></div></main><script>document.querySelector('form').addEventListener('submit', showLoading);</script></body></html>")
        body = "\n".join(html).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_paper_download(self):
        params = parse_qs(urlparse(self.path).query, encoding="utf-8", errors="ignore")
        query = params.get("q", [""])[0] or ""
        search_top_n = int(params.get("n", ["20"])[0])
        read_top_k = int(params.get("k", ["5"])[0])
        paper_top_n = int(params.get("p", ["6"])[0])
        channel = params.get("channel", ["domestic"])[0]
        html = [
            "<!doctype html><html><head><meta charset='utf-8'>",
            "<title>文献 PDF 导出</title>",
            f"<style>:root{{--body-bg:url('{bg_data_uri(bg_background_name())}');--header-bg:url('{bg_data_uri(bg_header_name())}');}}{PAGE_STYLE}</style></head><body>",
            f"<div class='loading' style='display:none'><div class='loading-card'><img class='mascot' src='{random_rock_url()}' alt='下载中'><h3>正在整理 PDF</h3><p class='hint'>正在尝试访问论文线索中的可下载文件。</p><div class='progress'><span></span></div></div></div>",
            "<main>",
        ]
        try:
            if not query or not is_hvac_query(query):
                raise RuntimeError("主题不在 HVAC 系统节能范围内，未执行下载")
            _, _, papers, _, _, _ = run_pipeline(query, search_top_n, read_top_k, channel, paper_top_n)
            report = download_paper_pdfs(papers, query, runtime_dir())
            html.append("<section><div class='status-hero'>")
            html.append(f"<img src='{random_rock_url()}' alt='导出完成'><div><h2>文献导出完成</h2><p>已在本地生成文献汇总文件夹。</p></div></div>")
            html.append(f"<p class='method-note'>保存位置：<code>{escape(report['folder'])}</code></p>")
            html.append(f"<p>成功下载：{len(report['saved'])} 个；未能下载：{len(report['failed'])} 个。</p>")
            if report["saved"]:
                html.append("<h3>已保存 PDF</h3>")
                for item in report["saved"]:
                    html.append(f"<p>{escape(item['title'])}<br><span class='meta'>{escape(item['file'])}</span></p>")
            if report["failed"]:
                html.append("<h3>未能直接下载的线索</h3>")
                for item in report["failed"][:12]:
                    html.append(f"<p>{escape(item['title'])}<br><span class='meta'>{escape(item['reason'])}</span></p>")
            html.append(f"<p><a class='download-link' href='/?q={quote(query)}&n={search_top_n}&k={read_top_k}&p={paper_top_n}&channel={quote(channel)}'>返回检索结果</a></p>")
            html.append("</section>")
        except Exception as exc:
            html.append(f"<section><div class='status-hero'><img src='{random_rock_url()}' alt='导出失败'><div><h2>文献导出未完成</h2><p>{escape(str(exc))}</p></div></div>")
            html.append(f"<p><a class='download-link' href='/?q={quote(query)}&n={search_top_n}&k={read_top_k}&p={paper_top_n}&channel={quote(channel)}'>返回检索结果</a></p></section>")
        html.append("</main></body></html>")
        body = "\n".join(html).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_rock_asset(self):
        name = unquote(Path(urlparse(self.path).path).name)
        asset = base_dir() / "洛克" / name
        if not asset.exists():
            self.send_response(404)
            self.end_headers()
            return
        data = asset.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/webp")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_favicon(self):
        asset = base_dir() / "juhuali.ico"
        if not asset.exists():
            self.send_response(404)
            self.end_headers()
            return
        data = asset.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/x-icon")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_bg_asset(self):
        parsed_path = urlparse(self.path).path
        if parsed_path == "/bg/background.png":
            name = bg_background_name()
            asset = base_dir() / "背景" / name
        elif parsed_path.startswith("/bg/icon/"):
            name = unquote(Path(parsed_path).name)
            asset = base_dir() / "背景" / "icons_clean" / name
        else:
            self.send_response(404)
            self.end_headers()
            return
        if not asset.exists():
            self.send_response(404)
            self.end_headers()
            return
        data = asset.read_bytes()
        content_type = "image/png" if asset.suffix.lower() == ".png" else "image/webp"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_server(host: str = "127.0.0.1", port: int = 8501) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8501"))
    server = create_server(host, port)
    print(f"Open http://{host}:{port}")
    server.serve_forever()
