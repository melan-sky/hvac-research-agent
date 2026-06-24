import html
import json
import re
import time
from pathlib import Path
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from models import SearchResult


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

COMMON_SEARCH_SUFFIX = "HVAC 暖通 空调 节能 建筑能源"
PAPER_SEARCH_SUFFIX = (
    "HVAC energy efficiency building control heat pump abstract "
    "site:sciencedirect.com/science/article"
)


class DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self._in_result = False
        self._in_title = False
        self._in_snippet = False
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "")
        if tag == "div" and "result" in classes and "result--ad" not in classes:
            self._in_result = True
            self._current = {"title": "", "url": "", "snippet": ""}
        if self._in_result and tag == "a" and "result__a" in classes:
            self._in_title = True
            self._current["url"] = clean_duck_url(attrs.get("href", ""))
        if self._in_result and tag in {"a", "div"} and "result__snippet" in classes:
            self._in_snippet = True

    def handle_endtag(self, tag):
        if self._in_title and tag == "a":
            self._in_title = False
        if self._in_snippet and tag in {"a", "div"}:
            self._in_snippet = False
        if self._in_result and tag == "div" and self._current:
            if self._current["title"] and self._current["url"]:
                self.results.append(self._current)
            self._in_result = False
            self._current = None

    def handle_data(self, data):
        if not self._current:
            return
        text = normalize_text(data)
        if not text:
            return
        if self._in_title:
            self._current["title"] += text + " "
        elif self._in_snippet:
            self._current["snippet"] += text + " "


def parse_duckduckgo_results(page: str) -> list[dict]:
    blocks = re.findall(
        r'(?is)<div class="result results_links.*?</div>\s*</div>\s*</div>',
        page,
    )
    parsed = []
    for block in blocks:
        title_match = re.search(
            r'(?is)<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            block,
        )
        snippet_match = re.search(
            r'(?is)<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            block,
        )
        if not title_match:
            continue
        title = normalize_text(re.sub(r"(?is)<[^>]+>", " ", title_match.group(2)))
        snippet = ""
        if snippet_match:
            snippet = normalize_text(re.sub(r"(?is)<[^>]+>", " ", snippet_match.group(1)))
        parsed.append(
            {
                "title": title,
                "url": clean_duck_url(title_match.group(1)),
                "snippet": snippet,
            }
        )
    return parsed


def strip_tags(fragment: str) -> str:
    return normalize_text(re.sub(r"(?is)<[^>]+>", " ", fragment))


def clean_so_url(url: str) -> str:
    url = html.unescape(url or "")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "u" in qs:
        return unquote(qs["u"][0])
    return url


def parse_so_results(page: str) -> list[dict]:
    blocks = re.findall(r'(?is)<li class="res-list".*?</li>', page)
    parsed = []
    for block in blocks:
        title_match = re.search(r'(?is)<h3[^>]*class="res-title[^"]*"[^>]*>\s*<a([^>]*)>(.*?)</a>', block)
        if not title_match:
            continue
        attrs = title_match.group(1)
        href_match = re.search(r'href="([^"]+)"', attrs)
        mdurl_match = re.search(r'data-mdurl="([^"]+)"', attrs)
        snippet_match = re.search(r'(?is)<p class="res-desc">(.*?)</p>', block)
        real_url = mdurl_match.group(1) if mdurl_match else href_match.group(1) if href_match else ""
        parsed.append(
            {
                "title": strip_tags(title_match.group(2)),
                "url": clean_so_url(real_url),
                "snippet": strip_tags(snippet_match.group(1)) if snippet_match else "",
            }
        )
    return parsed


def parse_bing_results(page: str) -> list[dict]:
    blocks = re.findall(r'(?is)<li class="b_algo".*?</li>', page)
    parsed = []
    for block in blocks:
        title_match = re.search(r'(?is)<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block)
        snippet_match = re.search(r'(?is)<p>(.*?)</p>', block)
        if not title_match:
            continue
        parsed.append(
            {
                "title": strip_tags(title_match.group(2)),
                "url": html.unescape(title_match.group(1)),
                "snippet": strip_tags(snippet_match.group(1)) if snippet_match else "",
            }
        )
    return parsed


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def clean_duck_url(url: str) -> str:
    url = html.unescape(url or "")
    if url.startswith("//duckduckgo.com/l/"):
        url = "https:" + url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "uddg" in qs:
        return unquote(qs["uddg"][0])
    return url


def get_domain(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain


def http_get(url: str, timeout: int = 8) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read(2_000_000)
        charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="ignore")


def http_get_bytes(url: str, timeout: int = 12, max_bytes: int = 30_000_000) -> tuple[bytes, str]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,text/html,*/*"})
    with urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise RuntimeError("文件超过 30MB，已跳过")
    return raw, content_type


def _items_to_results(parsed_items: list[dict], search_engine: str, search_top_n: int) -> list[SearchResult]:
    seen = set()
    results = []
    for item in parsed_items:
        clean_url = item["url"].strip()
        if not clean_url.startswith(("http://", "https://")):
            continue
        if clean_url in seen:
            continue
        seen.add(clean_url)
        results.append(
            SearchResult(
                title=normalize_text(item["title"]),
                url=clean_url,
                domain=get_domain(clean_url),
                snippet=normalize_text(item["snippet"]),
                search_engine=search_engine,
            )
        )
        if len(results) >= search_top_n:
            break
    return results


def _search_so(query: str, search_top_n: int) -> list[SearchResult]:
    search_engine = "360搜索"
    url = f"https://www.so.com/s?q={quote_plus(query)}"
    page = http_get(url, timeout=8)
    return _items_to_results(parse_so_results(page), search_engine, search_top_n)


def _search_bing_cn(query: str, search_top_n: int) -> list[SearchResult]:
    search_engine = "Bing 中国"
    url = f"https://cn.bing.com/search?q={quote_plus(query)}"
    page = http_get(url, timeout=8)
    return _items_to_results(parse_bing_results(page), search_engine, search_top_n)


def _search_duckduckgo(query: str, search_top_n: int) -> list[SearchResult]:
    search_engine = "DuckDuckGo HTML"
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    page = http_get(url, timeout=8)
    parsed_items = parse_duckduckgo_results(page)
    if not parsed_items:
        parser = DuckDuckGoParser()
        parser.feed(page)
        parsed_items = parser.results
    return _items_to_results(parsed_items, search_engine, search_top_n)


def search_web(query: str, search_top_n: int = 20, channel: str = "domestic") -> tuple[list[SearchResult], str]:
    hvac_query = f"{query} {COMMON_SEARCH_SUFFIX}"
    errors = []
    if channel == "international":
        engines = [
            ("Bing 国际/中国", _search_bing_cn),
            ("DuckDuckGo HTML", _search_duckduckgo),
            ("360搜索", _search_so),
        ]
    else:
        engines = [
            ("360搜索", _search_so),
            ("Bing 中国", _search_bing_cn),
            ("DuckDuckGo HTML", _search_duckduckgo),
        ]
    for search_engine, fn in engines:
        try:
            results = fn(hvac_query, search_top_n)
            if results:
                return results, search_engine
            errors.append(f"{search_engine}: 未解析到结果")
        except Exception as exc:
            errors.append(f"{search_engine}: {exc}")
    raise RuntimeError("国内优先搜索入口均失败；" + "；".join(errors))


def search_papers(query: str, paper_top_n: int = 6) -> tuple[list[SearchResult], str]:
    queries = [f"{query} {PAPER_SEARCH_SUFFIX}"]
    results = []
    engine = "360搜索（论文线索）"
    seen = set()
    for paper_query in queries:
        try:
            batch = _search_so(paper_query, paper_top_n)
        except Exception:
            batch = []
        for result in batch:
            if result.url in seen:
                continue
            seen.add(result.url)
            result.source_type = "论文线索"
            results.append(result)
            if len(results) >= paper_top_n:
                return results, engine

    if len(results) < max(2, paper_top_n // 2):
        for result in search_crossref_papers(query, paper_top_n - len(results)):
            if result.url not in seen:
                results.append(result)
    return results[:paper_top_n], engine + " + Crossref 公开论文元数据"


def search_crossref_papers(query: str, paper_top_n: int = 5) -> list[SearchResult]:
    if paper_top_n <= 0:
        return []
    crossref_query = f"{query} HVAC energy efficiency building"
    url = (
        "https://api.crossref.org/works?"
        f"rows={paper_top_n}&query.title={quote_plus(crossref_query)}"
    )
    page = http_get(url, timeout=8)
    data = json.loads(page)
    items = data.get("message", {}).get("items", [])
    results = []
    for item in items:
        titles = item.get("title") or []
        if not titles:
            continue
        title = normalize_text(titles[0])
        doi_url = item.get("URL") or ""
        publisher = item.get("publisher", "Crossref")
        year = ""
        date_parts = item.get("published-print", item.get("published-online", {})).get("date-parts", [])
        if date_parts and date_parts[0]:
            year = str(date_parts[0][0])
        abstract = strip_tags(item.get("abstract", ""))
        snippet = f"题录信息：{publisher}；{year}。摘要：{abstract}" if abstract else f"题录信息：{publisher}；{year}。Crossref 当前未提供摘要，请打开 DOI 页面核对。"
        result = SearchResult(
            title=title,
            url=doi_url,
            domain=get_domain(doi_url) if doi_url else "crossref.org",
            snippet=snippet,
            search_engine="Crossref 公开论文元数据",
            source_type="论文线索",
        )
        results.append(result)
    return results


def safe_filename(text: str, max_len: int = 90) -> str:
    text = normalize_text(text)
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" ._")
    return (text[:max_len].strip() or "paper")


def _candidate_pdf_urls(result: SearchResult) -> list[str]:
    url = result.url
    parsed = urlparse(url)
    candidates = []
    if parsed.path.lower().endswith(".pdf"):
        candidates.append(url)
    if "arxiv.org/abs/" in url:
        candidates.append(url.replace("/abs/", "/pdf/") + ".pdf")
    pii_match = re.search(r"/pii/([A-Za-z0-9]+)", url)
    if "sciencedirect.com" in parsed.netloc and pii_match:
        pii = pii_match.group(1)
        candidates.append(f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft?download=true")
    try:
        page = http_get(url, timeout=8)
    except Exception:
        page = ""
    if page:
        for pattern in [
            r'(?is)<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)',
            r'(?is)<meta[^>]+property=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)',
            r'(?is)<a[^>]+href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
            r'(?is)href=["\']([^"\']*(?:download|pdf)[^"\']*)["\']',
        ]:
            for match in re.findall(pattern, page):
                candidate = html.unescape(match)
                if candidate.startswith("//"):
                    candidate = "https:" + candidate
                elif candidate.startswith("/"):
                    candidate = urljoin(url, candidate)
                if candidate.startswith(("http://", "https://")):
                    candidates.append(candidate)
    unique = []
    seen = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def download_paper_pdfs(results: list[SearchResult], query: str, output_root: Path) -> dict:
    folder = output_root / f"{safe_filename(query, 36)}文献汇总"
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    failed = []
    for idx, result in enumerate(results, start=1):
        candidates = _candidate_pdf_urls(result)
        if not candidates:
            failed.append({"title": result.title, "reason": "没有发现可直接下载的 PDF 链接"})
            continue
        last_error = ""
        for pdf_url in candidates[:4]:
            try:
                data, content_type = http_get_bytes(pdf_url)
                is_pdf = data[:4] == b"%PDF" or "pdf" in content_type.lower()
                if not is_pdf:
                    last_error = "链接返回的不是 PDF 文件"
                    continue
                filename = f"{idx:02d}_{safe_filename(result.title)}.pdf"
                target = folder / filename
                target.write_bytes(data)
                saved.append({"title": result.title, "file": str(target), "url": pdf_url})
                break
            except Exception as exc:
                last_error = str(exc)
        else:
            failed.append({"title": result.title, "reason": last_error or "下载失败"})
    return {"folder": str(folder), "saved": saved, "failed": failed}


def extract_text_from_html(page: str) -> str:
    page = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", page)
    page = re.sub(r"(?is)<br\s*/?>", "\n", page)
    page = re.sub(r"(?is)</p>|</div>|</h[1-6]>", "\n", page)
    text = re.sub(r"(?is)<[^>]+>", " ", page)
    text = normalize_text(text)
    return text[:8000]


def extract_image_from_html(page: str, base_url: str) -> str:
    for pattern in [
        r'(?is)<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'(?is)<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
    ]:
        match = re.search(pattern, page)
        if match:
            image = html.unescape(match.group(1))
            if image.startswith("//"):
                return "https:" + image
            if image.startswith("/"):
                parsed = urlparse(base_url)
                return f"{parsed.scheme}://{parsed.netloc}{image}"
            return image
    return ""


def read_result_pages(results: list[SearchResult], read_top_k: int = 8) -> None:
    for result in results[:read_top_k]:
        try:
            time.sleep(0.08)
            page = http_get(result.url, timeout=5)
            text = extract_text_from_html(page)
            result.image_url = extract_image_from_html(page, result.url)
            if len(text) < 120:
                result.read_error = "正文过短或无法提取有效正文"
                continue
            result.content = text
            result.read_success = True
        except HTTPError as exc:
            result.read_error = f"HTTP {exc.code}"
        except URLError as exc:
            result.read_error = f"网络错误：{exc.reason}"
        except Exception as exc:
            result.read_error = f"读取失败：{exc.__class__.__name__}"
