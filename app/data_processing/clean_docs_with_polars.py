"""使用 Polars 清洗知识库文档。

功能：
- 去重
- 去除空白内容
- 内容长度过滤
- 文本标准化
- 按 Agent 分类统计
"""

import polars as pl


def clean_documents(docs: list[dict]) -> list[dict]:
    """清洗文档列表。"""
    if not docs:
        return []

    df = pl.DataFrame(docs)

    # 去除空白内容
    df = df.filter(pl.col("content").str.strip_chars().str.len_chars() > 0)

    # 去除过短内容（少于 50 字符）
    df = df.filter(pl.col("content").str.len_chars() >= 50)

    # 去重（基于 title + content 组合）
    df = df.unique(subset=["title", "content"])

    # 去除前后空白字符
    df = df.with_columns([
        pl.col("title").str.strip_chars(),
        pl.col("content").str.strip_chars(),
    ])

    return df.to_dicts()


def stats_by_agent(docs: list[dict]) -> dict:
    """按 Agent 统计文档数量。"""
    if not docs:
        return {}
    df = pl.DataFrame(docs)
    if "agent_name" not in df.columns:
        return {"total": len(docs)}

    stats = df.group_by("agent_name").agg(pl.count()).to_dict(as_series=False)
    result = {}
    for i, name in enumerate(stats["agent_name"]):
        result[name] = stats["count"][i]
    result["total"] = len(docs)
    return result


if __name__ == "__main__":
    print("Polars 文档清洗脚本。")
    print("用法: python -m app.data_processing.clean_docs_with_polars")
