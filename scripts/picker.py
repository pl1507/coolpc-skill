#!/usr/bin/env python3
"""
原價屋互動選購清單
用法：python3 picker.py
選完後自動開啟瀏覽器並填入估價單
"""

import json
import sys
from pathlib import Path

CACHE_FILE = Path("/tmp/coolpc_catalog.json")

# 一般組裝電腦會用到的類別（依順序顯示）
PC_CATEGORIES = [
    "處理器 CPU",
    "主機板 MB",
    "記憶體 RAM",
    "固態硬碟 M.2｜SSD",
    "2.5/3.5 傳統內接硬碟HDD",
    "顯示卡VGA",
    "CASE 機殼(+電源)",
    "電源供應器",
    "散熱器｜散熱墊｜散熱膏",
    "封閉式｜開放式水冷",
    "螢幕｜投影機｜壁掛",
    "鍵盤+鼠｜搖桿｜桌+椅",
    "滑鼠｜鼠墊｜數位板",
]


def load_catalog() -> list[dict]:
    if not CACHE_FILE.exists():
        print("找不到快取，請先執行：python3 scraper.py --refresh", file=sys.stderr)
        sys.exit(1)
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


def list_category(catalog: list[dict], category: str, budget: int | None = None) -> list[dict]:
    items = [r for r in catalog if r["category"] == category]
    if budget:
        items = [r for r in items if r["final_price"] <= budget]
    return sorted(items, key=lambda x: x["final_price"])


def print_items(items: list[dict], page: int = 0, page_size: int = 20):
    start = page * page_size
    end = min(start + page_size, len(items))
    print(f"\n  {'#':>4}  {'價格':>8}  {'折扣':>6}  商品名稱")
    print("  " + "-" * 80)
    for i, item in enumerate(items[start:end], start=start + 1):
        disc = f"-{item['discount']:,}" if item["discount"] else ""
        name = item["name"][:58]
        print(f"  {i:>4}  {item['final_price']:>8,}  {disc:>6}  {name}")
    if end < len(items):
        print(f"\n  （顯示 {start+1}–{end} / {len(items)} 項，輸入 'n' 看下一頁）")
    else:
        print(f"\n  （共 {len(items)} 項）")


def pick_items(catalog: list[dict]) -> dict[str, dict]:
    """互動式選購流程，回傳 {category: item}"""
    selected: dict[str, dict] = {}

    # 依序讓使用者選每個類別
    categories = [c for c in PC_CATEGORIES if any(r["category"] == c for r in catalog)]
    # 加上其他類別
    other_cats = sorted({r["category"] for r in catalog if r["category"] not in PC_CATEGORIES})
    all_cats = categories + other_cats

    print("\n" + "=" * 60)
    print("  原價屋估價單選購")
    print("=" * 60)
    print("  指令：輸入編號選擇，'s' 跳過，'n' 下一頁，'b' 上一頁，")
    print("        'f <關鍵字>' 搜尋，'q' 完成結帳")
    print("=" * 60)

    cat_idx = 0
    while cat_idx < len(all_cats):
        cat = all_cats[cat_idx]
        items = list_category(catalog, cat)
        if not items:
            cat_idx += 1
            continue

        already = selected.get(cat)
        already_str = f"（目前已選：{already['name'][:30]}）" if already else ""
        print(f"\n【 {cat} 】{already_str}")

        page = 0
        filtered_items = items

        while True:
            print_items(filtered_items, page)
            try:
                raw = input("\n  選擇> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n已中斷")
                return selected

            if raw.lower() == "q":
                return selected
            elif raw.lower() == "s":
                cat_idx += 1
                break
            elif raw.lower() == "n":
                if (page + 1) * 20 < len(filtered_items):
                    page += 1
            elif raw.lower() == "b":
                if page > 0:
                    page -= 1
            elif raw.lower().startswith("f "):
                keyword = raw[2:].strip().lower()
                filtered_items = [r for r in items if keyword in r["name"].lower()]
                page = 0
                if not filtered_items:
                    print(f"  找不到含「{keyword}」的商品，已重設")
                    filtered_items = items
            elif raw.isdigit():
                n = int(raw)
                if 1 <= n <= len(filtered_items):
                    chosen = filtered_items[n - 1]
                    selected[cat] = chosen
                    print(f"  ✓ 已選：{chosen['name'][:60]}  ${chosen['final_price']:,}")
                    cat_idx += 1
                    break
                else:
                    print(f"  請輸入 1–{len(filtered_items)} 之間的數字")

    return selected


def print_summary(selected: dict[str, dict]):
    if not selected:
        print("\n  未選任何商品")
        return

    total = 0
    print("\n" + "=" * 70)
    print("  估價單明細")
    print("=" * 70)
    print(f"  {'類別':20s}  {'售價':>8}  商品名稱")
    print("  " + "-" * 65)
    for cat, item in selected.items():
        cat_short = cat[:18]
        name = item["name"][:40]
        price = item["final_price"]
        total += price
        disc = f" (-{item['discount']:,})" if item["discount"] else ""
        print(f"  {cat_short:20s}  {price:>8,}{disc}  {name}")
    print("  " + "-" * 65)
    print(f"  {'合計':20s}  {total:>8,}")
    print("=" * 70)
    return total


def open_in_browser(selected: dict[str, dict]):
    """用 Playwright 開啟估價單並自動選好項目"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\n  未安裝 Playwright，無法自動開啟瀏覽器")
        print("  安裝方式：pip install playwright && playwright install chromium")
        return

    # 建立 {cat_idx: option_value} 的對應
    # 需要從 catalog 找回 idx
    catalog = load_catalog()
    # 建立 option_value → cat_idx 的反向查詢
    # cat_idx 存在 item 的 'idx' 欄位，category 字串對應 select name

    # 找出每個 category 的 nX 編號
    # 做法：先抓頁面取得 category labels，建立 label→n 的 map
    import ssl
    import urllib.request
    import re

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        "https://coolpc.com.tw/evaluate.php",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        raw = r.read()
    html = raw.decode("big5", errors="replace")

    # 建立 label → select_n 的 map
    cat_n_map: dict[str, int] = {}
    for m in re.finditer(r'<SELECT[^>]+name\s*=\s*n(\d+)', html, re.IGNORECASE):
        n = int(m.group(1))
        start = max(0, m.start() - 500)
        context = html[start:m.start()]
        td_t = re.findall(r'<TD[^>]+class=t[^>]*>([^<]{2,50})', context, re.IGNORECASE)
        if td_t:
            cat_n_map[td_t[-1].strip()] = n

    print("\n  正在開啟瀏覽器...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://coolpc.com.tw/evaluate.php")
        page.wait_for_load_state("networkidle")

        # 對每個已選項目，設定 select value
        for cat, item in selected.items():
            n = cat_n_map.get(cat)
            if n is None:
                print(f"  找不到類別 {cat} 的 select，跳過")
                continue
            opt_val = str(item["idx"])
            try:
                page.eval_on_selector(
                    f"select[name='n{n}']",
                    f"el => {{ el.value = '{opt_val}'; el.dispatchEvent(new Event('change')); }}"
                )
                print(f"  ✓ 已填：{cat[:20]} → {item['name'][:40]}")
            except Exception as e:
                print(f"  ✗ 填寫失敗 {cat}: {e}")

        print("\n  瀏覽器已開啟並自動填入選項")
        print("  請在瀏覽器中確認後按「列印估價單」或直接截圖")
        print("  （按 Enter 關閉瀏覽器）")
        input()
        browser.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="原價屋互動選購")
    parser.add_argument("--no-browser", action="store_true", help="只顯示清單，不開瀏覽器")
    args = parser.parse_args()

    catalog = load_catalog()
    selected = pick_items(catalog)

    if not selected:
        print("\n  未選任何商品，結束")
        return

    total = print_summary(selected)

    if not args.no_browser:
        ans = input("\n  是否開啟瀏覽器自動填入估價單？[Y/n] ").strip().lower()
        if ans != "n":
            open_in_browser(selected)
    else:
        print("\n  估價單連結：https://coolpc.com.tw/evaluate.php")
        print("  （請手動選擇上方商品）")


if __name__ == "__main__":
    main()
