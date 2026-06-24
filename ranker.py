import re
from urllib.parse import urlparse

from models import SearchResult


HVAC_TERMS = [
    "hvac", "暖通", "空调", "热泵", "节能", "能耗", "建筑能源", "控制",
    "智能", "变风量", "vav", "vrf", "冷水机组", "冷水机", "冷却塔", "需求响应", "预测控制",
    "楼宇自控", "楼控", "建筑自动化", "楼宇自动化", "bacs", "bms", "bems", "ddc",
    "新风", "通风", "制冷", "供热", "供冷", "冷媒", "制冷剂", "末端", "风机盘管",
    "ahu", "chiller", "ventilation", "refrigeration", "energy", "efficiency",
    "building", "heat pump", "demand response", "building automation",
]

CORE_SCOPE_TERMS = [
    "hvac", "暖通", "空调", "热泵", "制冷", "供热", "供冷", "通风", "新风",
    "冷水机", "冷却塔", "风机盘管", "变风量", "楼宇自控", "楼控", "建筑自动化",
    "建筑能源", "能源管理", "需求响应", "预测控制", "bacs", "bems", "bms", "vav",
    "vrf", "ahu", "chiller", "heat pump", "ventilation", "refrigeration",
]

WEAK_SCOPE_TERMS = [
    "建筑", "能源", "能效", "能耗", "节能率", "低碳", "降碳", "碳排放", "双碳",
    "冷热源", "冷源", "热源", "冷热", "机电", "建筑设备", "运行优化", "负荷",
    "用能", "耗电", "绿色建筑", "室内环境", "热舒适", "舒适性", "系统优化",
]

SOURCE_WEIGHTS = {
    "政府": 3.0,
    "高校": 2.8,
    "研究机构": 2.6,
    "论文线索": 2.5,
    "行业协会": 2.2,
    "企业": 1.4,
    "新闻": 1.0,
    "未知": 0.5,
}


def split_query(query: str) -> list[str]:
    parts = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", query.lower())
    return [p for p in parts if len(p.strip()) >= 2]


def query_scope(query: str) -> str:
    q = query.lower()
    if any(term.lower() in q for term in CORE_SCOPE_TERMS):
        return "core"
    if any(term.lower() in q for term in WEAK_SCOPE_TERMS):
        return "weak"
    return "none"


def is_hvac_query(query: str) -> bool:
    return query_scope(query) != "none"


def hvac_relevance_count(result: SearchResult) -> int:
    text = f"{result.title} {result.snippet} {result.content[:1200]}".lower()
    return sum(1 for term in CORE_SCOPE_TERMS if term.lower() in text)


def source_type(domain: str) -> str:
    d = domain.lower()
    if d.endswith(".gov") or ".gov." in d or d.endswith(".gov.cn"):
        return "政府"
    if d.endswith(".edu") or ".edu." in d or d.endswith(".edu.cn") or "university" in d:
        return "高校"
    if any(x in d for x in ["iea.org", "ashrae.org", "nist.gov", "lbl.gov", "energy.gov"]):
        return "研究机构"
    if any(x in d for x in ["sciencedirect.com", "springer.com", "mdpi.com", "nature.com", "sciencedirectassets.com"]):
        return "论文线索"
    if any(x in d for x in ["association", "ashrae", "society", "协会"]):
        return "行业协会"
    if any(x in d for x in ["carrier", "trane", "daikin", "johnsoncontrols", "midea", "gree"]):
        return "企业"
    if any(x in d for x in ["news", "cnr.cn", "people.com", "xinhuanet", "reuters"]):
        return "新闻"
    return "未知"


def invalid_result(result: SearchResult) -> bool:
    url = result.url.lower()
    path = urlparse(url).path.strip("/")
    bad_bits = ["login", "signin", "register", "search?", "/search/", "sitemap", "tag/", "category/"]
    if any(bit in url for bit in bad_bits):
        return True
    if path == "" and len(result.snippet) < 40:
        return True
    return False


def score_result(result: SearchResult, query: str) -> SearchResult:
    q_terms = split_query(query)
    text_title = result.title.lower()
    text_snippet = result.snippet.lower()
    text_content = result.content.lower()
    matched = []
    score = 0.0

    for term in q_terms:
        t = term.lower()
        if t in text_title:
            score += 5
            matched.append(f"标题:{term}")
        if t in text_snippet:
            score += 3
            matched.append(f"摘要:{term}")
        if result.read_success and t in text_content:
            score += 2
            matched.append(f"正文:{term}")

    for term in HVAC_TERMS:
        t = term.lower()
        if t in text_title:
            score += 1.4
            matched.append(f"领域词标题:{term}")
        elif t in text_snippet or (result.read_success and t in text_content):
            score += 0.7

    result.source_type = source_type(result.domain)
    score += SOURCE_WEIGHTS.get(result.source_type, 0.5)
    if invalid_result(result):
        score -= 8
        matched.append("疑似无效页")

    result.score = round(score, 2)
    result.matched_terms = matched[:12]
    return result


def rank_results(results: list[SearchResult], query: str) -> list[SearchResult]:
    scored = [score_result(r, query) for r in results]
    kept = [r for r in scored if r.score > 1.0 and not invalid_result(r) and hvac_relevance_count(r) > 0]
    kept.sort(key=lambda r: r.score, reverse=True)
    for idx, result in enumerate(kept, start=1):
        result.rank = idx
    return kept
