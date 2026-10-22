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
REQUEST_DELAY = 0.8
TIMEOUT = 15
MAX_RETRIES = 2

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


def request_json(url, params=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("request failed (%s/%s): %s -> %s", attempt, MAX_RETRIES, url, e)
            if attempt < MAX_RETRIES:
                time.sleep(1.5)
    return None


def fetch_users():
    data = request_json(LIST_API)
    if not data or "users" not in data:
        logger.error("failed to get user list")
        return []
    users = data["users"]
    logger.info("got %s accounts", len(users))
    return users


def fetch_password(account_id):
    data = request_json(PASS_API, params={"id": account_id})
    if not data:
        return None
    return data.get("password")


def normalize_region(country):
    name = (country or "未知").strip()
    code = REGION_MAP.get(name, "US")
    return code, name


def build_check_time(raw_time):
    now = datetime.now()
    if not raw_time:
        return now.strftime("%Y-%m-%d %H:%M:%S")

    raw_time = raw_time.strip()
    try:
        dt = datetime.strptime("%s-%s" % (now.year, raw_time), "%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    try:
        dt = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return now.strftime("%Y-%m-%d %H:%M:%S")


def crawl():
    users = fetch_users()
    if not users:
        raise RuntimeError("empty user list")

    group1 = []
    for idx, user in enumerate(users, start=1):
        uid = str(user.get("id") or ("auto-%s" % idx))
        email = (user.get("username") or "").strip()
        status = (user.get("status") or "未知").strip()
        raw_time = user.get("time")
        country = user.get("country")

        if not email:
            logger.warning("skip empty email: %s", uid)
            continue

        logger.info("[%s/%s] get password: %s", idx, len(users), email)
        password = fetch_password(uid)
        time.sleep(REQUEST_DELAY)

        if not password:
            logger.warning("password failed, skip: %s", email)
            continue

        region, region_name = normalize_region(country)
        check_time = build_check_time(raw_time)

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
            "vpn_ads": [],
        },
    }
    logger.info("done, %s accounts", len(group1))
    return result


def save_json(data, path):
    new_text = json.dumps(data, ensure_ascii=False, indent=4)
    old_text = ""
    if path.exists():
        old_text = path.read_text(encoding="utf-8")

    path.write_text(new_text, encoding="utf-8")
    changed = old_text.strip() != new_text.strip()
    logger.info("wrote %s (%s)", path, "changed" if changed else "unchanged")
    return changed


def main():
    try:
        data = crawl()
        save_json(data, OUTPUT_FILE)
        logger.info("task finished")
    except Exception as e:
        logger.error("task failed: %s", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
