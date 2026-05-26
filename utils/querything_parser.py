"""
解析 querything.md 文件，提取结构化的查询主题列表。

querything.md 格式：
  ## 分类名 ⭐⭐⭐ 优先级
  | 主题关键词 | 监测平台 | 备注 |
  |-----------|---------|------|
  | xxx | 微博、抖音 | 说明 |
"""

import re
from pathlib import Path
from typing import Optional


def parse_querything(filepath: str) -> dict:
    """解析 querything.md，返回分类和主题列表。"""
    path = Path(filepath)
    if not path.exists():
        return {"categories": [], "topics": []}

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    categories = []
    topics = []
    current_category = ""
    current_priority = 3
    in_table = False

    for line in lines:
        stripped = line.strip()

        # H2 标题 → 分类 + 优先级
        if stripped.startswith("## ") and not stripped.startswith("### "):
            in_table = False
            current_category, current_priority = _parse_category_header(stripped)
            if current_category:
                categories.append({
                    "name": current_category,
                    "priority": current_priority,
                })

        # 表格分隔符 |---| 或表头 | 主题关键词 | ...
        if stripped.startswith("|") and stripped.endswith("|"):
            if _is_table_separator(stripped):
                in_table = True
                continue
            if _is_table_header(stripped):
                in_table = True
                continue

            if in_table and current_category:
                topic = _parse_topic_row(stripped, current_category, current_priority)
                if topic:
                    topics.append(topic)

    return {"categories": categories, "topics": topics}


def get_query_keywords(filepath: str) -> list[str]:
    """提取所有查询关键词（用于自动搜索）。"""
    result = parse_querything(filepath)
    return [t["keyword"] for t in result["topics"]]


def _parse_category_header(line: str) -> tuple[str, int]:
    """解析 '## 一、集团品牌声誉 ⭐⭐⭐ 高' → (名称, 优先级)"""
    text = line[3:].strip()  # 去掉 "## "

    # 提取星级
    star_match = re.search(r"(⭐+)\s*(高|中|低)?", text)
    if star_match:
        stars = star_match.group(1)
        priority = stars.count("⭐")
        text = text[: star_match.start()].strip()
    else:
        priority = 3  # 默认高

    # 去掉数字编号如 "一、" "1."
    text = re.sub(r"^[一二三四五六七八九十\d]+[、.]\s*", "", text)

    return text, priority


def _is_table_separator(line: str) -> bool:
    """判断是否为 Markdown 表格分隔行，如 |---|---|"""
    return bool(re.match(r"^\|[\s\-:|]+\|$", line))


def _is_table_header(line: str) -> bool:
    """判断是否为表格表头行"""
    headers = ["主题关键词", "监测平台", "备注", "优先级"]
    return any(h in line for h in headers)


def _parse_topic_row(line: str, category: str, priority: int) -> Optional[dict]:
    """解析表格行，如 | 海珠湾隧道 | 微博、小红书 | 重点工程 |"""
    cells = [c.strip() for c in line.strip("|").split("|")]
    if len(cells) < 1 or not cells[0]:
        return None

    keyword = cells[0]
    platforms = cells[1] if len(cells) > 1 else "全平台"
    note = cells[2] if len(cells) > 2 else ""

    return {
        "keyword": keyword,
        "category": category,
        "priority": priority,
        "platforms": platforms,
        "note": note,
    }
