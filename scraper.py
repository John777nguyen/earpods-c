#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quét trang "Máy đổi trả - Tai nghe Apple" trên thegioididong.com,
phát hiện khi có sản phẩm EarPods xuất hiện (còn hàng để bán),
và gửi thông báo qua Telegram.

Trạng thái (đã từng thông báo hay chưa cho từng sản phẩm) được lưu
trong state.json để tránh spam tin nhắn mỗi lần chạy — chỉ báo khi
có SẢN PHẨM MỚI xuất hiện so với lần quét trước.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.thegioididong.com/may-doi-tra/tai-nghe-apple"
STATE_FILE = Path(__file__).parent / "state.json"

# Từ khoá nhận diện sản phẩm EarPods (không phân biệt hoa/thường)
KEYWORD = "earpods"

# Các cụm từ cho biết sản phẩm đang HẾT HÀNG (nếu xuất hiện gần tên sp)
OUT_OF_STOCK_MARKERS = ["hết hàng", "tạm hết hàng", "ngừng kinh doanh", "sắp có hàng"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


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
    resp.raise_for_status()
    return resp.text


def find_earpods_items(html: str):
    """
    Trả về list các dict {name, url} cho từng sản phẩm có chứa từ khoá
    "EarPods" và KHÔNG bị đánh dấu hết hàng.

    Trang thegioididong thường liệt kê sản phẩm trong các thẻ <li class="item">
    bên trong <ul class="listproduct">, mỗi item có 1 thẻ <a> chứa href và tên
    sản phẩm (thường trong thuộc tính data-name hoặc thẻ con h3).
    Nếu cấu trúc trang thay đổi, hàm find_earpods_items_fallback() bên dưới
    sẽ được dùng như phương án dự phòng (quét toàn bộ thẻ <a> trong trang).
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # --- Cách 1: parse theo cấu trúc listproduct > li.item (cấu trúc phổ biến của TGDD) ---
    items = soup.select("ul.listproduct li.item") or soup.select("li.item")

    for item in items:
        text_block = item.get_text(" ", strip=True)
        if KEYWORD not in text_block.lower():
            continue

        link_tag = item.find("a", href=True)
        name = None
        # Ưu tiên data-name nếu có (TGDD hay gắn data-name cho mục đích tracking)
        if link_tag and link_tag.has_attr("data-name"):
            name = link_tag["data-name"]
        elif item.find("h3"):
            name = item.find("h3").get_text(strip=True)
        else:
            name = text_block[:120]

        url = link_tag["href"] if link_tag else URL
        if url.startswith("/"):
            url = "https://www.thegioididong.com" + url

        lower_block = text_block.lower()
        is_out_of_stock = any(marker in lower_block for marker in OUT_OF_STOCK_MARKERS)

        if not is_out_of_stock:
            results.append({"name": name, "url": url})

    if results:
        return results

    # --- Cách 2 (dự phòng): quét toàn bộ thẻ <a> trong trang có chứa "EarPods" ---
    return find_earpods_items_fallback(soup)


def find_earpods_items_fallback(soup: BeautifulSoup):
    results = []
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if KEYWORD in text.lower() and text not in seen:
            url = a["href"]
            if url.startswith("/"):
                url = "https://www.thegioididong.com" + url
            seen.add(text)
            results.append({"name": text, "url": url})
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
        sys.exit(0)  # không fail workflow chỉ vì lỗi mạng tạm thời

    items = find_earpods_items(html)
    current_names = {it["name"] for it in items}

    new_items = [it for it in items if it["name"] not in notified]

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

    # Cập nhật state: giữ lại các sản phẩm hiện đang có trên trang
    # (khi sản phẩm biến mất rồi xuất hiện lại sau này sẽ được báo lại)
    state["notified_products"] = list(current_names)
    save_state(state)


if __name__ == "__main__":
    main()
