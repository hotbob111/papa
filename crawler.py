#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 shareid.tools12345.com 拉取账号列表和密码，
生成符合现有网站格式的 api_data.json
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path

import requests

# ============== 配置 ==============
BASE_URL = "https://shareid.tools12345.com"
LIST_API = f"{BASE_URL}/proxy.php?api=get-users"
PASS_API = f"{BASE_URL}/proxy.php?api=get-password"

OUTPUT_FILE = Path(__file__).parent / "api_data.json"
REQUEST_DELAY = 0.8          # 每次请求间隔（秒）
TIMEOUT = 15                 # 单次请求超时
MAX_RETRIES = 2              # 失败重试次数

# 国家名 -> 地区代码简单映射
REGION_MAP = {
    "美国": "US",
    "美区": "US",
    "台湾": "TW",
    "香港": "HK",
    "日本": "JP",
    "韩国": "KR",
    "英国": "GB",
    "越南": "VN",
    "中国大陆": "CN",
    "未知": "US",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL + "/",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def request_json(url: str, params: dict | None = None) -> dict | None:
    """带重试的 GET JSON 请求"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"请求失败 ({attempt}/{MAX_RETRIES}): {url} -> {e}")
            if attempt < MAX_RETRIES:
                time.sleep(1.5)
    return None


def fetch_users() -> list[dict]:
    """获取账号列表"""
    data = request_json(LIST_API)
    if not data or "users" not in data:
        logger.error("获取账号列表失败或格式异常")
        return []
    users = data["users"]
    logger.info(f"获取到 {len(users)} 个账号")
    return users


def fetch_password(account_id: str) -> str | None:
    """根据 id 获取密码"""
    data = request_json(PASS_API, params={"id": account_id})
    if not data:
        return None
    return data.get("password")


def normalize_region(country: str | None) -> tuple[str, str]:
    """返回 (region代码, regionName)"""
    name = (country or "未知").strip()
    code = REGION_MAP.get(name, "US")
    return code, name


def build_check_time(raw_time: str | None) -> str:
    """
    把原站的 time（如 10-22 19:55）尽量转成完整时间。
    解析失败则使用当前时间。
    以账号自身的检测时间为准。
    """
    now = datetime.now()
    if not raw_time:
        return now.strftime("%Y-%m-%d %H:%M:%S")

    raw_time = raw_time.strip()
    # 尝试 "MM-DD HH:MM"
    try:
        dt = datetime.strptime(f"{now.year}-{raw_time}", "%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    # 已经是完整时间就直接用
    try:
        dt = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return now.strftime("%Y-%m-%d %H:%M:%S")


def crawl() -> dict:
    """主爬取流程"""
    users = fetch_users()
    if not users:
        raise RuntimeError("账号列表为空，中止本次任务")

    group1 = []
    for idx, user in enumerate(users, start=1):
        uid = str(user.get("id") or f"auto-{idx}")
        email = (user.get("username") or "").strip()
        status = (user.get("status") or "未知").strip()
        raw_time = user.get("time")
        country = user.get("country")

        if not email:
            logger.warning(f"跳过无邮箱账号: {uid}")
            continue

        logger.info(f"[{idx}/{len(users)}] 获取密码: {email}")
        password = fetch_password(uid)
        time.sleep(REQUEST_DELAY)

        if not password:
            logger.warning(f"密码获取失败，跳过: {email}")
            continue

        region, region_name = normalize_region(country)
        check_time = build_check_time(raw_time)  # 以账号更新时间为准

        group1.append({
            "id": uid,
            "fullEmail": email,
            "password": password,
            "status": status,
            "checkTime": check_time,
            "region": region,
            "regionName": region_name,
        })

    result = {
        "timestamp": int(time.time()),
        "data": {
            "accounts": {
                "group1": group1,
                "group2": [],
            },
            "vpn_ads": [],          # 本地同步脚本会保留原有 VPN 数据
        },
    }
    logger.info信息(f"本次成功处理 {len长度(    日志记录器。info信息(f"本次成功处理 {len长度(group1)} 个账号")组1)} 个账号")组1)} 个账号")
    return返回 result结果


def save_json(data: dict, path: Path) -> bool:
    """写入文件，返回是否与旧文件内容不同"""
    new_text = json.dumps(data, ensure_ascii=False, indent=4)
    old_text = ""
    if path.exists():    如果路径.存在():
        old_text = path.read_text(encoding="utf-8")        旧文本 = 路径.读取文本(编码="utf-8")

    path.write_text(new_text, encoding="utf-8")    路径。write_text(新文本，编码="utf-8")
    changed = old_text.strip() != new_text.strip()    变化 = 旧文本。strip() != 新文本。strip()
    logger.info信息(f"已写入 {path} （{'有变化' if changed else '无变化'}）")已更改else '无变化'}）")
    return changed已更改


def main主分支():
    try:
        data = crawl()
        changed = save_json(data, OUTPUT_FILE)数据，OUTPUT_FILE)
        # 给 GitHub Actions 用：有变化退出码 0，可配合后续步骤判断是否 commit        # 供 GitHub Actions 使用：有变化时退出码为 0，可配合后续步骤判断是否 commit        # 供 GitHub Actions 使用：有变化时退出码为 0，可配合后续步骤判断是否 commit        # 供 GitHub Actions 使用：有变化时退出码为 0，可配合后续步骤判断是否 commit        # 供 GitHub Actions 使用：有变化时退出码为 0，可配合后续步骤判断是否 commit        # 供 GitHub Actions 使用：有变化时退出码为 0，可配合后续步骤判断是否 commit
        # 这里统一成功退出
        logger.info信息("任务完成")
    except Exception as e:
        logger.error(f"任务失败: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main主分支()    主函数()
