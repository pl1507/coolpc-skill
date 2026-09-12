#!/usr/bin/env python3
"""
原價屋估價單解析器
抓取 https://coolpc.com.tw/evaluate.php 並解析所有商品與現價
"""

import json
import re
import ssl
import sys
import urllib.request
from pathlib import Path

CACHE_FILE = Path("/tmp/coolpc_catalog.json")

MAX_CATEGORIES = 30


def fetch_page() -> str:
    """下載並解碼 Big5 頁面"""
    url = "https://coolpc.com.tw/evaluate.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        raw = resp.read()

    # 先試 Big5，失敗改 utf-8
    for enc in ("big5", "cp950", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_js_array(html: str, name: str) -> list:
    """從 JS 原始碼抓出 name=[...] 陣列"""
    # 匹配 c1=[...] 或 d1=[...] 等
    pattern = rf'\b{re.escape(name)}\s*=\s*\[([^\]]*)\]'
    m = re.search(pattern, html)
    if not m:
        return []
    raw = m.group(1).strip()
    if not raw:
        return []
    items = []
    for token in raw.split(","):
        token = token.strip()
        try:
            items.append(int(token))
        except ValueError:
            try:
                items.append(float(token))
            except ValueError:
                items.append(0)
    return items


def extract_select_options(html: str) -> dict[str, list[str]]:
    """
    解析所有 <select> 的 <option> 文字，回傳 {select_name: [option_text, ...]}
    第 0 個 option 通常是「請選擇」佔位，保留以對齊 JS 陣列索引
    """
    selects = {}
    # 找每個 <select ... name="XX">
    for sel_m in re.finditer(r'<select[^>]+name=["\']?(\w+)["\']?[^>]*>(.*?)</select>',
                              html, re.DOTALL | re.IGNORECASE):
        sel_name = sel_m.group(1)
        sel_body = sel_m.group(2)
        options = []
        for opt_m in re.finditer(r'<option[^>]*>(.*?)</option>',
                                  sel_body, re.DOTALL | re.IGNORECASE):
            text = re.sub(r'<[^>]+>', '', opt_m.group(1)).strip()
            options.append(text)
        if options:
            selects[sel_name] = options
    return selects


def extract_category_labels(html: str) -> dict[int, str]:
    """從每個 <select name=nX> 前方的 TD/class=t 文字取得類別標籤"""
    labels = {}
    for m in re.finditer(r'<SELECT[^>]+name\s*=\s*n(\d+)', html, re.IGNORECASE):
        idx = int(m.group(1))
        start = max(0, m.start() - 500)
        context = html[start:m.start()]

        # 優先找 <TD class=t>...</TD> 格式（原價屋實際結構）
        td_t = re.findall(r'<TD[^>]+class=t[^>]*>([^<]{2,50})', context, re.IGNORECASE)
        if td_t:
            labels[idx] = td_t[-1].strip()
            continue

        # 備援：找最後一個有意義的文字節點
        texts = re.findall(r'>([^<]{2,40})<', context)
        label = texts[-1].strip() if texts else f"類別{idx}"
        labels[idx] = label
    return labels


def parse_product_names(html: str) -> dict[int, dict[int, str]]:
    """
    解析 <select name=n1>, <select name=n2>, ... 的 option 文字
    回傳 {cat_idx: {option_value: name}}
    option text 格式：「產品名稱【現貨】, $價格 ★」，取逗號前為名稱
    """
    sel_pattern = re.compile(
        r'<SELECT[^>]+name\s*=\s*n(\d+)[^>]*>(.*?)</SELECT>',
        re.DOTALL | re.IGNORECASE
    )
    result = {}
    for m in sel_pattern.finditer(html):
        cat_idx = int(m.group(1))
        body = m.group(2)
        opts = {}
        for opt_m in re.finditer(
            r'<OPTION(?![^>]*disabled)[^>]+value\s*=\s*(\d+)[^>]*>([^<]+)',
            body, re.IGNORECASE
        ):
            val = int(opt_m.group(1))
            raw_text = opt_m.group(2).strip()
            # 取逗號前（去掉後面的 $價格 ★ 部分）
            name = raw_text.split(',')[0].strip()
            if name:
                opts[val] = name
        if opts:
            result[cat_idx] = opts
    return result


def full_catalog(html: str) -> list[dict]:
    """
    回傳完整商品清單，每筆包含 category / name / price / discount / final_price
    """
    names_map  = parse_product_names(html)
    cat_labels = extract_category_labels(html)
    records    = []

    for cat_idx in range(1, MAX_CATEGORIES + 1):
        prices    = extract_js_array(html, f"c{cat_idx}")
        discounts = extract_js_array(html, f"d{cat_idx}")
        if not prices:
            continue

        cat_name  = cat_labels.get(cat_idx, f"類別{cat_idx}")
        cat_names = names_map.get(cat_idx, {})

        while len(discounts) < len(prices):
            discounts.append(0)

        for i, price in enumerate(prices):
            if price == 0:
                continue
            name = cat_names.get(i, f"#{i}")
            disc = discounts[i]
            records.append({
                # idx = option value（evaluate.php 的 option value 即 JS 陣列索引），
                # picker.py 開瀏覽器自動填入時需要此欄位
                "idx": i,
                "category": cat_name,
                "name": name,
                "price": price,
                "discount": disc,
                "final_price": price - disc,
            })

    return records


def main():
    import argparse
    parser = argparse.ArgumentParser(description="原價屋估價單爬蟲")
    parser.add_argument("--refresh", action="store_true", help="強制重新抓取")
    parser.add_argument("--category", help="只顯示特定類別（例如 CPU）")
    parser.add_argument("--budget", type=int, help="顯示低於此金額的商品")
    args = parser.parse_args()

    if args.refresh or not CACHE_FILE.exists():
        print("正在抓取原價屋估價單...", file=sys.stderr)
        html = fetch_page()
        records = full_catalog(html)
        CACHE_FILE.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"已快取 {len(records)} 筆商品至 {CACHE_FILE}", file=sys.stderr)
    else:
        records = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        print(f"讀取快取：{len(records)} 筆商品", file=sys.stderr)

    # 篩選
    if args.category:
        records = [r for r in records if args.category.lower() in r["category"].lower()]
    if args.budget:
        records = [r for r in records if r["final_price"] <= args.budget]

    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
