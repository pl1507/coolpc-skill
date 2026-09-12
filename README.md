# coolpc-skill

抓取 [原價屋](https://www.coolpc.com.tw/evaluate.php) 估價單頁面的即時商品與價格，協助你依預算與需求快速討論、篩選並組合電腦零件。提供 CLI 查價與互動式選購兩種模式。

> 本工具僅供個人參考使用；商品資料版權歸原價屋所有。

## 功能特色

- 🕷️ **即時抓取**：直接讀取估價單頁面，取得當日最新商品名稱、定價、折扣與實際售價
- 🔍 **分類 / 預算篩選**：按 CPU、主機板、顯示卡等類別查詢，或篩選低於指定預算的商品
- 💾 **快取機制**：當日快取避免重複抓取，跨日自動重新整理
- 🖥️ **互動式選購**（選配）：以數字鍵挑選零件、即時計算合計金額
- 🌐 **瀏覽器自動填入**（選配）：選完零件後自動開啟瀏覽器填入官方估價單
- 📦 **零依賴**：核心功能僅需 Python 3 標準函式庫（urllib / re / json），不需 pip install

## 環境需求

- Python 3.8+（`urllib`、`re`、`json` 皆為內建模組）
- (Optional)互動式選購 + 瀏覽器自動填入：需選配安裝 [Playwright](https://playwright.dev/python/) 與 Chromium（未安裝時自動降級為純清單模式，不影響查價）

```bash
pip install playwright
playwright install chromium
```

## 使用方法

### 1. 抓取估價單

```bash
python3 scripts/scraper.py --refresh    # 強制重新抓取（建議每日第一次執行）
python3 scripts/scraper.py              # 讀取當日快取（存在且當天有效時）
```

抓取結果會輸出至 `/tmp/coolpc_catalog.json`；若快取不存在或已跨日，會自動重新抓取。

### 2. 分類與預算篩選

```bash
# 只顯示特定類別
python3 scripts/scraper.py --category "CPU"
python3 scripts/scraper.py --category "顯示卡"

# 分類 + 預算上限
python3 scripts/scraper.py --category "主機板" --budget 5000
```

可用分類關鍵字：

| 分類 | 關鍵字 |
|------|--------|
| 處理器 | `CPU` |
| 主機板 | `主機板` |
| 記憶體 | `RAM` |
| 固態硬碟 | `SSD` |
| 顯示卡 | `顯示卡` |
| 機殼 | `CASE` |
| 電源 | `電源` |
| 散熱器 | `散熱` |
| 螢幕 | `螢幕` |
| 筆電 | `筆電` |
| 套裝電腦 | `套裝` |

### 3. 互動式選購

```bash
python3 scripts/picker.py                # 選完自動開瀏覽器填入官方估價單（需 Playwright）
python3 scripts/picker.py --no-browser   # 只顯示清單與合計，不開瀏覽器
```

操作方式：

| 按鍵 | 功能 |
|------|------|
| `<數字>` | 選擇商品 |
| `s` | 跳過目前類別 |
| `n` / `b` | 下一頁 / 上一頁 |
| `f <關鍵字>` | 搜尋 |
| `q` | 完成選購並結算 |

未安裝 Playwright 時會提示安裝方式並自動降級為純清單模式。

## 輸出資料格式

每筆商品為一組 JSON 物件：

```json
{
  "idx": 3,
  "category": "處理器 CPU",
  "name": "Intel Core i5-14600K【現貨】",
  "price": 8990,
  "discount": 500,
  "final_price": 8490
}
```

| 欄位 | 說明 |
|------|------|
| `idx` | 估價單下拉選單的 option value，供 `picker.py` 自動填入用 |
| `category` | 商品所屬分類 |
| `name` | 商品名稱（含【現貨】表示有庫存、【訂】表示需訂購） |
| `price` | 定價 |
| `discount` | 折扣金額（大於 0 代表有限時優惠） |
| `final_price` | 實際售價 = price − discount |

## 專案結構

```
coolpc/
├── README.md            # 本文件
├── SKILL.md             # OpenClaw Agent Skill 說明（供 AI 助理使用）
└── scripts/
    ├── scraper.py       # 爬蟲：抓取估價單、快取、分類/預算篩選
    └── picker.py        # 互動式選購 CLI（選配 Playwright 自動填入）
```

## 已知限制與錯誤處理

| 情況 | 處理方式 |
|------|---------|
| SSL 憑證錯誤 | 爬蟲已關閉憑證驗證，正常情況不會發生 |
| 抓取逾時 | 重新執行 `python3 scripts/scraper.py --refresh` |
| 商品名稱顯示 `#N` | 原價屋頁面結構異動，請回報 issue；可先以既有快取繼續使用 |
| 快取不存在 | 自動觸發重新抓取 |

## 注意事項

- 原價屋估價單（evaluate.php）沒有可分享的 GET URL；如需分享明細，請在瀏覽器中按「列印估價單」產生可列印／截圖頁面
- 請勿高頻率、大量抓取，避免對網站造成負擔
