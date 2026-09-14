#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quét trang "Máy đổi trả - Tai nghe Type-C" trên thegioididong.com,
phát hiện khi có sản phẩm EarPods xuất hiện (còn hàng để bán),
và gửi thông báo qua Telegram.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Trang tổng hợp Tai nghe Type-C (mọi hãng) — EarPods (USB-C) của Apple sẽ
# xuất hiện ở đây nếu đang mở bán.
URL = "https://www.thegioididong.com/may-doi-tra/tai-nghe?g=type-c"
STATE_FILE = Path(__file__).parent / "state.json"

KEYWORD = "earpods"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

PID_RE = re.compile(r"[?&]pid=(\d+)")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"notified_products": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    print(f"[DEBUG] HTTP status: {resp.status_code}, độ dài HTML: {len(resp.text)} ký tự")
    resp.raise_for_status()
    return resp.text


def find_earpods_items(html: str):
    soup = BeautifulSoup(html, "html.parser")

    all_links = soup.find_all("a", href=True)
    product_links = [a for a in all_links if PID_RE.search(a["href"])]

    print(f"[DEBUG] Tổng số thẻ <a>: {len(all_links)}, "
          f"số link sản phẩm (có pid=): {len(product_links)}")

    raw_has_keyword = KEYWORD in html.lower()
    print(f"[DEBUG] Từ khoá '{KEYWORD}' có xuất hiện trong HTML thô: {raw_has_keyword}")

    results = []
    seen_pids = set()

    for a in product_links:
        href = a["href"]
        match = PID_RE.search(href)
        pid = match.group(1) if match else href

        if pid in seen_pids:
            continue

        text = a.get_text(" ", strip=True)
        if KEYWORD not in text.lower():
            continue

        seen_pids.add(pid)
        url = href if href.startswith("http") else "https://www.thegioididong.com" + href
        results.append({"pid": pid, "name": text, "url": url})

    return results


def send_telegram_message(text: str) -> None:
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        print("[LỖI] Thiếu TG_BOT_TOKEN hoặc TG_CHAT_ID trong biến môi trường.")
        sys.exit(1)

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(api_url, data=payload, timeout=30)
    if not resp.ok:
        print(f"[LỖI] Gửi Telegram thất bại: {resp.status_code} {resp.text}")


def main():
    state = load_state()
    notified = set(state.get("notified_products", []))

    try:
        html = fetch_html(URL)
    except requests.RequestException as e:
        print(f"[LỖI] Không tải được trang: {e}")
        sys.exit(0)

    items = find_earpods_items(html)
    print(f"[DEBUG] Số sản phẩm EarPods tìm thấy: {len(items)} -> "
          f"{[it['name'] for it in items]}")

    current_pids = {it["pid"] for it in items}
    new_items = [it for it in items if it["pid"] not in notified]

    if new_items:
        lines = ["🎧 <b>EarPods vừa xuất hiện trên trang Máy đổi trả TGDD!</b>", ""]
        for it in new_items:
            lines.append(f"• {it['name']}\n{it['url']}")
        lines.append("")
        lines.append(URL)
        send_telegram_message("\n".join(lines))
        print(f"[OK] Đã thông báo {len(new_items)} sản phẩm mới: "
              f"{[it['name'] for it in new_items]}")
    else:
        print("[OK] Không có EarPods mới (hoặc chưa có hàng).")

    state["notified_products"] = list(current_pids)
    save_state(state)


if __name__ == "__main__":
    main()
