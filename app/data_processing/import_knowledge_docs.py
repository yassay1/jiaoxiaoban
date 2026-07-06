"""知识库文档导入脚本。

支持从 CSV、Excel 批量导入知识文档，使用 Polars 进行数据清洗和格式化。
"""

import polars as pl
from pathlib import Path


def import_from_csv(file_path: str, agent_name: str = "") -> list[dict]:
    """从 CSV 文件导入知识文档。

    CSV 应包含列: title, content, source_type (可选)
    """
    df = pl.read_csv(file_path)
    if "title" not in df.columns or "content" not in df.columns:
        raise ValueError("CSV 文件必须包含 'title' 和 'content' 列")

    docs = []
    for row in df.iter_rows(named=True):
        docs.append({
            "title": row["title"],
            "content": row["content"],
            "source_type": row.get("source_type", "csv_import"),
            "agent_name": agent_name,
        })
    return docs


def import_from_excel(file_path: str, sheet_name: str = "Sheet1", agent_name: str = "") -> list[dict]:
    """从 Excel 文件导入知识文档。"""
    df = pl.read_excel(file_path, sheet_name=sheet_name)
    if "title" not in df.columns or "content" not in df.columns:
        raise ValueError("Excel 文件必须包含 'title' 和 'content' 列")

    docs = []
    for row in df.iter_rows(named=True):
        docs.append({
            "title": row["title"],
            "content": row["content"],
            "source_type": row.get("source_type", "excel_import"),
            "agent_name": agent_name,
        })
    return docs


if __name__ == "__main__":
    print("知识库文档导入脚本。")
    print("用法: python -m app.data_processing.import_knowledge_docs")
