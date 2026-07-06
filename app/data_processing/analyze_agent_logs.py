"""使用 Polars 分析 Agent 运行日志。

功能：
- 按 Graph 类型统计运行次数
- 统计成功/失败率
- 统计 Tool 调用频率
- 按时间段分析请求量
"""

import polars as pl
from datetime import datetime


def analyze_agent_runs(runs: list[dict]) -> dict:
    """分析 Agent 运行记录。"""
    if not runs:
        return {"error": "无运行记录"}

    df = pl.DataFrame(runs)

    # 按 Graph 类型统计
    graph_stats = {}
    if "graph_name" in df.columns:
        graph_counts = df.group_by("graph_name").agg(pl.count()).to_dict(as_series=False)
        for i, name in enumerate(graph_counts["graph_name"]):
            graph_stats[name] = graph_counts["count"][i]

    # 成功率统计
    success_rate = 0.0
    if "status" in df.columns:
        total = len(df)
        succeeded = df.filter(pl.col("status") == "completed").height
        success_rate = succeeded / total if total > 0 else 0.0

    return {
        "total_runs": len(runs),
        "by_graph": graph_stats,
        "success_rate": round(success_rate, 4),
    }


def analyze_tool_calls(tool_calls: list[dict]) -> dict:
    """分析 Tool 调用记录。"""
    if not tool_calls:
        return {"error": "无 Tool 调用记录"}

    df = pl.DataFrame(tool_calls)

    tool_stats = {}
    if "tool_name" in df.columns:
        tool_counts = df.group_by("tool_name").agg(pl.count()).to_dict(as_series=False)
        for i, name in enumerate(tool_counts["tool_name"]):
            tool_stats[name] = tool_counts["count"][i]

    return {
        "total_tool_calls": len(tool_calls),
        "by_tool": tool_stats,
    }


if __name__ == "__main__":
    print("Agent 日志分析脚本。")
    print("用法: python -m app.data_processing.analyze_agent_logs")
