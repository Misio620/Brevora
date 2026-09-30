# 設計過程

Brevora 從桌面工具演變成 Web App 的過程中留下的設計稿，以及 Logo 與介面的決策紀錄。

HTML 檔直接用瀏覽器開啟即可檢視。

| 檔案 | 內容 |
|------|------|
| `reference-ui-v0-desktop.png` | 最早的版本「YouTube RSS 訂閱通知」（Electron 桌面 App）介面，Brevora 的起點 |
| `logo-concepts-v1.html` | Logo 第一輪：4 個方向 |
| `logo-concepts-v2.html` | Logo 第二輪：4 個方向 |
| `logo-concepts-v3.html` | Logo 第三輪：6 個方向 |
| `logo-concepts-v4.html` | Logo 第四輪：6 個方向 |

---

## 從通知工具到 AI 筆記

最早的版本只負責通知訂閱頻道有新影片。問題是：只有輸入、沒有輸出，不會帶來太多成長。有了筆記，才會逼自己產出，輸入也才能更廣、更深。所以產品的核心從「通知有新影片」變成「先讀懂影片重點，再決定要不要看原片」。

## Logo

### 四輪探索

| 輪次 | 探索的方向 | 方案 |
|------|------------|------|
| v1 | 速度、影片、筆記 | Fast Forward Summary、Page + Play、Abstract B、Lightning + Play |
| v2 | 時間：取名字 *brevis*（簡短）+ *ora*（時間）的意涵 | Hourglass、Compress、Speed Clock、B + Hourglass |
| v3 | 延續 v2，加入閱讀與「內容濃縮」的概念 | Hourglass、Compress、Speed Clock、B-Hourglass、Fast Reader、Portal |
| v4 | 粗重、各以單一幾何概念構成的圖形 | The Notch B、The Pinch、Three to One、The Fold、Speed Mark、The Lens |

### 結果

- 四輪的方案都沒有採用，原因很單純：看起來不夠好看
- 目前產品上用的是 Instrument Serif 斜體的文字標誌「Brevora」，favicon 是同字體的「B」。這是暫時版本
- 之後會重新設計，做出自己滿意的 Logo
- 這幾輪都沒有請其他人看過或提供意見

## 介面

### 視覺風格

深色毛玻璃（glassmorphism）風格是暫時的，之後會再調整。

### 筆記結構

筆記的格式由我提出需求，和 Claude 討論後定案：一句話主題 → 摘要 → 五個關鍵要點 → 延伸重點 → 行動呼籲。

- **五個關鍵要點**：五點大致就能知道影片全貌
- **時間戳**：每個要點都附時間戳，點擊後跳到原片的那一秒，可以回頭看

### UX 修正

最初版本（2026 年 3 月）修正的 19 項 UX 問題（無障礙、觸控、手機版、操作回饋等）由 Claude 審查找出。整理作品集時修正的其他問題，見 [決策紀錄](../decisions.md#5-影響信任的-bug-修正)。

### 放棄的設計

目前還沒有。
