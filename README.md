# coolpc-skill

Claude Code skill，抓取[原價屋](https://coolpc.com.tw/evaluate.php)估價單的即時商品與價格，協助討論預算與零件搭配。

## 安裝

```bash
bash install.sh
```

## 使用方式

安裝後，在任何 Claude Code 對話中提到「原價屋」、「組電腦」、「預算搭配」等關鍵字，skill 會自動觸發。

範例：
- 「我想在原價屋組電腦，預算 4 萬，主要打遊戲」
- 「幫我看看原價屋 CPU 哪個 CP 值最高」
- 「5 萬預算的影片剪輯電腦怎麼搭？」

## 檔案結構

```
coolpc-skill/
├── install.sh       # 安裝 script
└── coolpc/
    ├── SKILL.md     # Skill 定義與流程
    ├── scraper.py   # 估價單爬蟲
    └── picker.py    # 互動選購 + 自動填入瀏覽器
```

## picker.py 用法（互動選購）

```bash
cd coolpc

# 互動選購，選完自動開啟瀏覽器填入估價單
python3 picker.py

# 只顯示清單與合計，不開瀏覽器
python3 picker.py --no-browser
```

操作指令：`<數字>` 選擇、`s` 跳過、`n/b` 換頁、`f <關鍵字>` 搜尋、`q` 完成

> 需要 Playwright：`pip install playwright && playwright install chromium`

## scraper.py 用法

```bash
cd coolpc

# 抓取並快取所有商品
python3 scraper.py --refresh

# 讀取快取（不重新抓取）
python3 scraper.py

# 篩選類別
python3 scraper.py --category CPU
python3 scraper.py --category 顯示卡

# 篩選預算
python3 scraper.py --category 主機板 --budget 5000
```

輸出為 JSON，快取於 `/tmp/coolpc_catalog.json`。
