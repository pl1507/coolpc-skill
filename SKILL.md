---
name: coolpc
description: 抓取原價屋（coolpc.com.tw）估價單頁面的即時商品與價格，協助使用者依預算與需求討論最佳零件搭配方案。當使用者提到「原價屋」、「組電腦」、「預算搭配」、「零件推薦」、「coolpc」、「估價單」時請使用此 skill。
---

# 原價屋估價單 Skill

協助使用者依預算與需求，從原價屋（coolpc.com.tw/evaluate.php）的即時商品清單討論最適合的零件搭配組合。

## 環境

- Skill 路徑：`${HOME}/.openclaw/skills/coolpc`；**所有指令先 `cd "${HOME}/.openclaw/skills/coolpc"`** 再執行 `python3 scripts/...`（下方指令皆假設已在此目錄）
- `scraper.py`／`picker.py` 皆為 **Python 3 stdlib only**（urllib/re/json），不需要 venv、不需要 pip install；直接 `python3` 即可
- 商品快取：`/tmp/coolpc_catalog.json`（當日有效；跨日或想拿最新價一律加 `--refresh`）
- `picker.py` 的瀏覽器自動填入需選配 Playwright（未安裝時會提示並降級），純查價/推薦流程用不到它

## 整體流程

```
1. 抓取估價單  →  2. 了解需求與預算  →  3. 推薦搭配  →  4. 討論微調  →  5. (選配)開啟估價單
```

---

## Step 1：抓取原價屋估價單

### 執行爬蟲

```bash
python3 scripts/scraper.py --refresh
```

- 輸出快取至 `/tmp/coolpc_catalog.json`
- 若快取已存在（當天），省略 `--refresh` 直接讀快取：

```bash
python3 scripts/scraper.py 2>/dev/null
```

### 資料格式

每筆商品包含：
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

> `idx` = 估價單 select 的 option value，供 picker.py 自動填入用。

### 查詢特定類別

```bash
python3 scripts/scraper.py --category "CPU" 2>/dev/null
python3 scripts/scraper.py --category "顯示卡" 2>/dev/null
python3 scripts/scraper.py --category "主機板" --budget 5000 2>/dev/null
```

可用類別（依頁面）：
| 分類 | 關鍵字 |
|------|--------|
| 處理器 | CPU |
| 主機板 | 主機板 |
| 記憶體 | RAM |
| 固態硬碟 | SSD |
| 顯示卡 | 顯示卡 |
| 機殼 | CASE |
| 電源 | 電源 |
| 散熱器 | 散熱 |
| 螢幕 | 螢幕 |
| 筆電 | 筆電 |
| 套裝電腦 | 套裝 |

---

## Step 2：了解需求與預算

若使用者尚未說明，請先詢問以下資訊：

1. **總預算**：多少元？（例如：30,000、50,000、100,000）
2. **主要用途**：
   - 日常辦公 / 文書
   - 遊戲（哪些遊戲？目標解析度？）
   - 影音剪輯 / 創作
   - 3D 繪圖 / CAD
   - AI / 深度學習
   - 程式開發
3. **已有零件**：有沒有可沿用的舊零件？
4. **特殊偏好**：品牌、尺寸（ITX/ATX）、靜音、RGB 等

---

## Step 3：推薦搭配

### 讀取商品資料

```python
import json
catalog = json.load(open('/tmp/coolpc_catalog.json'))

def get_category(keyword):
    return [r for r in catalog if keyword.lower() in r['category'].lower()]

def within_budget(items, budget):
    return [r for r in items if r['final_price'] <= budget]

def search(keyword):
    kw = keyword.lower()
    return [r for r in catalog if kw in r['name'].lower()]
```

### 預算分配建議（一般遊戲主機）

| 用途 | CPU | 顯示卡 | 主機板 | 記憶體 | 硬碟 | 電源 | 機殼 | 散熱 |
|------|-----|--------|--------|------|------|------|------|------|
| 入門（3萬） | 20% | 35% | 12% | 10% | 8% | 8% | 5% | 5% |
| 中階（5萬） | 18% | 38% | 12% | 8% | 7% | 8% | 5% | 4% |
| 高階（10萬） | 20% | 40% | 12% | 8% | 8% | 7% | 3% | 3% |

### 推薦格式

列出推薦組合時，請依此格式呈現：

```
## 💻 推薦組合：[用途名稱] — 預算 $XX,XXX

| 零件 | 型號 | 定價 | 折扣 | 實際售價 |
|------|------|------|------|---------|
| CPU  | ...  | ...  | -... | $...    |
| 主機板 | ... | ... | -... | $...    |
| ...  | ...  | ...  | -... | $...    |
| **合計** | | | | **$XX,XXX** |

### 搭配說明
- [說明相容性、為何選這組合]
- [效能預期]
- [升級空間]

### 替代方案
- 預算更低：...
- 效能更高：...
```

### 相容性注意事項

推薦時**必須確認**：
- CPU 與主機板腳位相符（Intel LGA1700/LGA1851、AMD AM4/AM5）
- DDR4 / DDR5 記憶體與主機板規格一致
- 電源瓦數足夠（CPU TDP + GPU TDP + 20% 餘裕）
- 機殼支援主機板規格（ATX / mATX / ITX）
- M.2 SSD 介面（PCIe 3.0 / 4.0 / 5.0）與主機板相符

---

## Step 4：討論微調

使用者可能的後續問題：
- 「這張顯卡值得嗎？」→ 查同類別比價，說明 CP 值
- 「有沒有更便宜的主機板？」→ 篩選同腳位但低價選項
- 「我想加 SSD」→ 在剩餘預算內推薦
- 「這個有貨嗎？」→ 商品名稱含【現貨】代表有庫存，【訂】代表需訂購

### 價格異動提醒

若商品名稱包含 `discount > 0`，代表有限時折扣，提醒使用者把握時機。

---

## Step 5：（選配）開啟估價單

互動式選購（需要 TTY；純查價/推薦不需要）：

```bash
python3 scripts/picker.py --no-browser        # 只顯示清單與合計（無 Playwright 也能用）
python3 scripts/picker.py                     # 選完自動開瀏覽器填入（需 Playwright+Chromium）
```

操作方式：`<數字>` 選擇、`s` 跳過、`n/b` 換頁、`f <關鍵字>` 搜尋、`q` 完成。
未安裝 Playwright 時自動降級並提示安裝方式，不影響選購清單功能。

> **注意**：原價屋估價單（evaluate.php）沒有可分享的 GET URL，選好商品後需在瀏覽器中按「列印估價單」產生可列印/截圖明細頁。

---

## 錯誤處理

| 情況 | 處理方式 |
|------|---------|
| SSL 憑證錯誤 | scraper.py 已跳過驗證，正常情況不會發生 |
| 抓取逾時 | 重新執行 `python3 scripts/scraper.py --refresh` |
| 商品名稱顯示 `#N` | 頁面結構異動，回報並使用快取資料繼續討論 |
| 快取不存在 | 自動觸發 `--refresh` 重新抓取 |
