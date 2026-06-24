from collections import Counter
import re

from models import SearchResult
from ranker import HVAC_TERMS, split_query


def _top_terms(results: list[SearchResult]) -> list[str]:
    text = " ".join((r.title + " " + r.snippet + " " + r.content[:1000]).lower() for r in results)
    counts = Counter()
    for term in HVAC_TERMS:
        if term.lower() in text:
            counts[term] += text.count(term.lower())
    return [term for term, _ in counts.most_common(8)]


def _source_line(result: SearchResult) -> str:
    source_type = "" if result.source_type in {"未知", ""} else f"，{result.source_type}"
    detail_text = source_summary(result)
    if detail_text:
        label = "正文摘录" if result.read_success and result.content else "搜索页摘要"
        detail = f"{label}：{detail_text}"
    else:
        detail = "说明：该来源只提供了题名或元数据，需打开原文页面继续核对。"
    return f"- {result.title}\n  来源：{result.domain}{source_type}\n  {detail}"


def source_summary(result: SearchResult, limit: int = 260) -> str:
    text = (result.content if result.read_success and result.content else result.snippet).strip()
    text = " ".join(text.split())
    if not text:
        return ""
    if not (result.read_success and result.content) and "..." in text:
        return ""
    text = _clean_source_text(text)
    abstract_match = re.search(r"(摘要|摘 要)[:：]\s*(.{40,})", text)
    if abstract_match:
        text = abstract_match.group(2)
    elif result.read_success and result.content:
        text = _best_relevant_passage(text, result.title)
    text = _clean_source_text(text)
    text = _focus_body_text(text)
    text = _clean_source_text(text)
    if _looks_like_noise_summary(text):
        return ""
    text = _complete_text(text)
    if not text:
        return ""
    if len(text) <= limit:
        return text
    candidates = [text.rfind(mark, 0, limit) for mark in ["。", "；", ";", ".", "！", "？"]]
    cut = max(candidates)
    if cut >= 90:
        return text[: cut + 1]
    return text[:limit].rstrip("，,、;； ") + "。"


def _clean_source_text(text: str) -> str:
    noise_patterns = [
        r"首页\s+期刊导航\s+论文中心\s+期刊检索\s+论文检索\s+新闻中心\s+期刊\s+期刊论文",
        r"当前位置[:：]?.{0,180}",
        r"首页\s*>\s*论文详情\s*>.{0,160}",
        r"手机知网\s+App\s+24小时专家级知识服务\s+打\s*开",
        r"手机知网.{0,220}充值中心",
        r"建筑科学与工程\s+手机知网首页\s+文献检索\s+期刊\s+工具书\s+图书\s+我的知网\s+充值中心",
        r"拖动LOGO到书签栏.{0,120}",
        r"首页\s+商城\s+IC.{0,160}",
        r"原创力文档\s+知识共享平台.{0,120}",
        r"Skip to navigation\s+Skip to content.{0,220}",
        r"Close X\s+About Us\s+What We Do.{0,160}",
        r"您可能关注的文档.{0,500}",
        r"相关文档.{0,300}",
        r"推荐文档.{0,300}",
        r"最近下载.{0,800}",
        r"VIP\s+.{0,800}",
        r"26版.{0,800}",
        r"2026版企业.{0,800}",
        r"初级健康.{0,800}",
        r"高考物理.{0,800}",
        r"开通知网号",
        r"登录|注册|收藏|充值中心|我的知网",
    ]
    cleaned = text
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.I)
    cleaned = re.sub(r"(首页|期刊导航|论文中心|期刊检索|论文检索|新闻中心|期刊论文|论文详情|作者|阅读)\s*[:：]?", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_>|")
    return cleaned


def _focus_body_text(text: str) -> str:
    starts = ["本文即", "本文旨在", "本文从", "本文提出", "本文分析", "研究表明", "研究发现", "近年来", "随着"]
    for marker in starts:
        pos = text.find(marker)
        if 0 <= pos <= 180:
            return text[pos:].strip()
    return text


def _looks_like_noise_summary(text: str) -> bool:
    electronics = ["CAN", "LIN", "MCU", "MOTOR DRIVER", "TRANSCEIVER", "单片机", "收发器", "微控制器"]
    if sum(1 for term in electronics if term.lower() in text.lower()) >= 3:
        return True
    doc_markers = [".docx", ".pptx", ".pdf", "模板", "题库", "真题"]
    if sum(text.lower().count(term.lower()) for term in doc_markers) >= 4:
        return True
    nav_markers = ["首页", "导航", "登录", "注册", "商城", "下载", "充值中心"]
    if sum(1 for term in nav_markers if term in text) >= 4:
        return True
    return False


def _complete_text(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if text[-1] in "。！？.!?":
        return text
    last = max(text.rfind(mark) for mark in ["。", "！", "？", ".", "!", "?"])
    if last >= 45:
        return text[: last + 1]
    return ""


def _best_relevant_passage(text: str, title: str) -> str:
    terms = ["暖通", "空调", "HVAC", "热泵", "节能", "能耗", "建筑", "控制", "通风", "制冷", "能源"]
    title_terms = [w for w in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", title) if len(w) >= 2]
    terms.extend(title_terms[:6])
    pieces = re.split(r"(?<=[。！？；;.!?])\s*", text)
    candidates = []
    for piece in pieces:
        p = piece.strip()
        if len(p) < 35:
            continue
        noise_hits = sum(1 for noise in ["首页", "期刊导航", "当前位置", "登录", "注册", "书签栏", "商城", "导航", "About Us", "What We Do"] if noise in p)
        if noise_hits >= 2:
            continue
        score = sum(1 for term in terms if term.lower() in p.lower())
        if score:
            candidates.append((score, len(p), p))
    if candidates:
        candidates.sort(key=lambda x: (x[0], min(x[1], 240)), reverse=True)
        return candidates[0][2]
    return ""


def _topic_label(query: str, terms: list[str]) -> str:
    text = (query + " " + " ".join(terms)).lower()
    if any(x in text for x in ["热泵", "heat pump"]):
        return "热泵与高效冷热源"
    if any(x in text for x in ["楼宇自控", "楼控", "建筑自动化", "bacs", "bms", "ddc"]):
        return "楼宇自控与建筑自动化"
    if any(x in text for x in ["预测控制", "需求响应", "智能控制", "ai", "demand response"]):
        return "智能控制与需求响应"
    if any(x in text for x in ["变风量", "vav", "末端", "风机盘管"]):
        return "空气侧与末端系统优化"
    return "HVAC 系统节能"


def build_newsletter(
    query: str,
    search_engine: str,
    raw_count: int,
    read_success_count: int,
    kept_results: list[SearchResult],
) -> str:
    terms = _top_terms(kept_results)
    q_terms = "、".join(split_query(query)) or query
    important = kept_results[:5]
    topic_label = _topic_label(query, terms)

    findings = []
    if any(t in terms for t in ["热泵", "heat pump"]):
        findings.append("热泵相关结果集中在高效冷热源、低碳供热供冷和系统能效提升，适合作为 HVAC 节能的设备侧方向。")
    if any(t in terms for t in ["控制", "智能", "预测控制", "demand response"]):
        findings.append("智能控制、预测控制和需求响应相关内容较多，说明 HVAC 节能正从单设备效率提升转向系统运行优化。")
    if any(t in terms for t in ["building", "建筑能源", "energy"]):
        findings.append("多条结果把 HVAC 与建筑能源管理联系起来，说明该方向需要结合建筑负荷、运行时段和用户需求综合评价。")
    if len(findings) < 3 and any(r.source_type in {"高校", "研究机构", "论文线索"} for r in kept_results):
        findings.append("结果中包含论文、高校或研究机构线索，适合继续追踪方法、实验工况和节能率口径。")
    if len(findings) < 3 and any(r.source_type in {"企业", "新闻"} for r in kept_results):
        findings.append("结果中包含企业方案或新闻资料，可用于了解产品化方向，但节能效果需要与论文或标准交叉核对。")
    if len(findings) < 3:
        findings.append("当前资料可作为主题入口，但仍需要补充更权威的论文、标准或工程案例。")

    source_lines = "\n".join(_source_line(r) for r in important) or "- 暂无可保留来源。"
    finding_lines = "\n".join(f"{i}. {item}" for i, item in enumerate(findings[:3], start=1))

    return f"""HVAC 系统节能技术检索小报

研究主题：{query}

主题归类：{topic_label}

资料概况：本次共整理 {raw_count} 条联网资料线索，其中 {read_success_count} 条完成正文读取，{len(kept_results)} 条进入分析列表。检索来源：{search_engine}。

核心发现
{finding_lines}

重要来源
{source_lines}

针对问题的回答：围绕“{q_terms}”检索到的资料显示，该问题可归入“{topic_label}”。已有资料主要能回答技术原理、应用场景和工程方案层面的问题；若需要定量比较节能率，还需要继续锁定论文、标准或工程实测资料。

需核对信息：不同资料的工况、节能率口径和应用场景可能不一致；部分页面无法读取正文；企业页面中的节能表述需要与论文或标准资料交叉核对。

下一步整理方向：补充近三年英文论文和标准资料；优先比较高校、研究机构、行业协会与企业资料；围绕关键技术路线整理适用场景、节能机理和代表性产品。
"""
