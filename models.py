from dataclasses import dataclass, field


@dataclass
class SearchResult:
    title: str
    url: str
    domain: str
    snippet: str
    search_engine: str = "DuckDuckGo HTML"
    content: str = ""
    read_success: bool = False
    read_error: str = ""
    score: float = 0.0
    source_type: str = "未知"
    matched_terms: list[str] = field(default_factory=list)
    rank: int = 0
    image_url: str = ""


@dataclass
class SearchReport:
    query: str
    search_engine: str
    raw_count: int
    read_success_count: int
    kept_count: int
    results: list[SearchResult]
    newsletter: str
    debug: dict
