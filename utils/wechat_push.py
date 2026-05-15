"""
Server酱 微信推送模块

通过 Server酱 推送消息到微信。
需要 SERVERCHAN_SENDKEY 环境变量配置。
申请地址: https://sct.ftqq.com/
"""

import re
import httpx
from loguru import logger


def _build_url(sendkey: str) -> str:
    """根据 SendKey 构造 Server酱 3 的推送 URL"""
    match = re.match(r"sctp(\d+)", sendkey)
    if match:
        uid = match.group(1)
        return f"https://{uid}.push.ft07.com/send/{sendkey}.send"
    # 兜底：直接拼接
    return f"https://sc3.ft07.com/{sendkey}.send"


def _get_sendkey() -> str:
    """获取 Server酱 SendKey，优先从项目配置读取"""
    try:
        from config import settings
        return settings.SERVERCHAN_SENDKEY or ""
    except Exception:
        import os
        return os.getenv("SERVERCHAN_SENDKEY", "")


def send(title: str, content: str = "", tags: str = "") -> bool:
    """
    推送消息到微信

    Args:
        title: 消息标题（必填，最长 120 字）
        content: 消息内容（可选，支持 Markdown）
        tags: 标签（可选）

    Returns:
        bool: 是否推送成功
    """
    sendkey = _get_sendkey()
    if not sendkey:
        logger.warning("SERVERCHAN_SENDKEY 未配置，跳过微信推送")
        return False

    url = _build_url(sendkey)
    payload = {"title": title[:120]}

    if content:
        payload["desp"] = content
    if tags:
        payload["tags"] = tags

    try:
        resp = httpx.post(url, data=payload, timeout=15)
        result = resp.json()
        if result.get("code") == 0:
            logger.info(f"微信推送成功: {title}")
            return True
        else:
            logger.error(f"微信推送失败: {result.get('message', '未知错误')}")
            return False
    except Exception as e:
        logger.error(f"微信推送异常: {e}")
        return False


def push_report(task_id: str, query: str, report_path: str) -> bool:
    """
    推送报告完成通知到微信

    Args:
        task_id: 任务 ID
        query: 查询关键词
        report_path: 报告文件路径

    Returns:
        bool: 是否推送成功
    """
    title = f"舆情报告完成: {query[:40]}"
    content = (
        f"## 舆情监测报告\n\n"
        f"**查询主题:** {query}\n\n"
        f"**任务 ID:** {task_id}\n\n"
        f"**报告路径:** {report_path}\n\n"
        f"---\n"
        f"*由 BettaFish 舆情监测系统自动推送*"
    )
    return send(title, content, tags="舆情报告")
