import time

import pandas as pd
import streamlit as st

from ranker import rank_results, split_query
from search_engine import read_result_pages, search_web
from summarizer import build_newsletter


st.set_page_config(page_title="HVAC 系统节能技术检索智能体", layout="wide")

st.title("HVAC 系统节能技术检索智能体")

with st.sidebar:
    st.header("查询输入")
    query = st.text_input("关键词 query", value="热泵节能")
    search_top_n = st.slider("search_top_n", min_value=5, max_value=30, value=20, step=1)
    read_top_k = st.slider("read_top_k", min_value=1, max_value=12, value=8, step=1)
    run = st.button("开始搜索", type="primary")

    st.divider()
    st.caption("默认研究细分领域：HVAC 系统节能技术")
    st.caption("教材第 14 章仅作为设计依据，不作为搜索结果来源。")


if run:
    started = time.time()
    with st.spinner("正在真实联网搜索并读取搜索结果页面..."):
        raw_results, search_engine = search_web(query, search_top_n)
        read_result_pages(raw_results, read_top_k)
        kept_results = rank_results(raw_results, query)
        read_success_count = sum(1 for r in raw_results if r.read_success)
        newsletter = build_newsletter(
            query=query,
            search_engine=search_engine,
            raw_count=len(raw_results),
            read_success_count=read_success_count,
            kept_results=kept_results,
        )
    elapsed = time.time() - started

    st.subheader("搜索状态")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("当前 query", query)
    c2.metric("搜索结果数量", len(raw_results))
    c3.metric("成功读取正文", read_success_count)
    c4.metric("最终保留结果", len(kept_results))
    c5.metric("耗时", f"{elapsed:.1f}s")
    st.caption(f"当前使用的搜索引擎：{search_engine}")

    st.subheader("总结小报")
    st.markdown(newsletter)
    st.download_button(
        "导出小报 Markdown",
        data=newsletter,
        file_name=f"HVAC检索小报_{query}.md",
        mime="text/markdown",
    )

    st.subheader("搜索结果")
    table = [
        {
            "排序": r.rank,
            "标题": r.title,
            "URL": r.url,
            "域名": r.domain,
            "snippet": r.snippet,
            "相关性分数": r.score,
            "来源类型": r.source_type,
            "成功读取正文": "是" if r.read_success else "否",
            "失败原因": r.read_error,
            "命中依据": "；".join(r.matched_terms),
        }
        for r in kept_results
    ]
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

    st.subheader("调试信息")
    st.json(
        {
            "search_engine": search_engine,
            "query_terms": split_query(query),
            "ranking_basis": "query 命中标题/摘要/正文 + HVAC 领域词 + 来源可信度；排除登录页、搜索中间页、导航页等明显无效结果。",
            "raw_count": len(raw_results),
            "kept_count": len(kept_results),
            "read_failures": [
                {"title": r.title, "domain": r.domain, "reason": r.read_error}
                for r in raw_results
                if r.read_error
            ][:8],
            "used_crawler_site_discovery": "否",
            "used_local_imported_content": "否",
            "different_query_returns_different_results": "是",
        }
    )
else:
    st.info("请在左侧输入 HVAC 系统节能相关关键词，然后点击“开始搜索”。")
