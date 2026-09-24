# 決策紀錄

記錄 Brevora 從「自己用的工具」整理成「可公開展示的作品」時做的關鍵決策：當時的限制、考慮過的選項、依據的證據，以及接受的取捨。

程式碼由 AI（Claude Code）撰寫；以下的問題定義、選項取捨與優先順序由我決定。

---

## 1. 作品集用「前端 Demo 模式」部署，不採用 Supabase

**限制**

- 面試官會從履歷上的連結自己點開，時間可能是投遞後幾天，也可能是幾週後
- 必須免登入就能體驗核心價值：訂閱影片 → AI 節目筆記
- 只用免費方案

**考慮過的選項**

| 選項 | 問題 |
|------|------|
| 完整部署（FastAPI + PostgreSQL + Google 登入） | 訪客要用 Google 帳號登入並授權 YouTube 權限，對只想花一分鐘看作品的面試官門檻太高 |
| Supabase 免費方案當資料庫 | 免費專案一週沒有資料庫活動就會被暫停（[官方文件](https://supabase.com/docs/guides/platform/free-project-pausing)）。履歷連結的點擊頻率遠低於一週一次，面試官點開時很可能剛好遇上暫停 |
| **前端 Demo 模式 + 預先生成的真實資料（採用）** | 無法即時為新影片生成筆記 |

**決策**

- 前端設定 `VITE_DEMO_MODE=true` 時，API 呼叫改由瀏覽器內的 demo 層回應（`frontend/src/lib/demo.ts`），畫面與正式版是同一套元件
- 筆記用 `scripts/generate_demo_data.py` 產生：它呼叫的是產品本身的 `app.services.ai`，所以 demo 呈現的就是產品的實際輸出，不是手寫範例
- 收藏、已讀、釘選頻道存在訪客自己的瀏覽器（localStorage），可以實際操作
- Vercel 靜態部署，沒有伺服器會休眠或暫停
- 正式版 build 不會打包 demo 資料（demo 程式以動態載入切成獨立檔案，只有 demo build 才會產生）

**取捨**

- Demo 只有 6 支影片，「同步」與「生成筆記」不會真的執行，畫面會說明原因
- 完整版仍保留在 repo，可依 README 在本機執行

---

## 2. YouTube 封鎖雲端主機 → 改由 Gemini 直接讀影片網址

**問題**

原本取得影片內容有兩條路：用 `youtube-transcript-api` 抓字幕，抓不到時用 `yt-dlp` 下載音訊再交給 AI。兩條路都要伺服器直接連 youtube.com，而 YouTube 會對雲端主機的 IP 回傳機器人驗證頁。

**證據**

2026-09-24 在雲端容器中重現：

```bash
curl -sL -A "Mozilla/5.0 ..." "https://www.youtube.com/watch?v=8BtHk-oNlN0"
```

- HTTP 狀態碼是 200，但頁面內容是驗證頁，不是影片
- 頁面中的 `playabilityStatus` 為 `LOGIN_REQUIRED`
- 頁面文字：「Sign in to confirm you're not a bot」

所以這不是「偶爾失敗」：只要部署到雲端，字幕與音訊兩條路都拿不到內容。在本機開發時不容易察覺這個問題。

**決策**

- 把 YouTube 網址直接交給 Gemini（`file_data`），由 Google 端讀取影片，伺服器不再接觸 youtube.com
- 移除 `yt-dlp`、`youtube-transcript-api`、`ffmpeg`，部署需求變少
- 影片標題、頻道、長度等資料改用官方的 YouTube Data API v3（用 API key 驗證，不受機器人驗證影響）

**實測**

2026-09-24 生成 demo 資料（`gemini-3.6-flash`、低媒體解析度）：

| 影片 | 長度 | 生成時間 |
|------|------|----------|
| How I AI — Opus 5.5 與 GPT-6 Sol 實測 | 38 分 | 46 秒 |
| How I AI — 7 個 Grok Bot 代理 | 36 分 | 82 秒 |
| The Diary Of A CEO — Andrew Huberman | 136 分 | 127 秒 |
| The Diary Of A CEO — 億萬富豪警告 | 105 分 | 122 秒 |
| Starter Story — Roblox 百萬富翁 | 20 分 | 39 秒 |
| Starter Story — 複製 3 款 App | 13 分 | 37 秒 |

兩小時以上的影片也能在約兩分鐘內完成。另外用 REST API 測過一支 13.6 分鐘的影片，約消耗 7.4 萬 tokens。

**取捨**

- 只支援公開影片
- 依賴 Gemini 對 YouTube 網址的支援
- Gemini 免費方案每天最多處理 8 小時的 YouTube 影片（[官方文件](https://ai.google.dev/gemini-api/docs/video-understanding)），所以 demo 資料生成腳本會跳過已完成的影片，額度用完隔天可以接著跑

---

## 3. Gemini 舊模型退役 → 模型名稱改為可設定

**問題**

程式寫死 `gemini-2.5-flash`，備援是 `gemini-2.5-flash-lite`。Google 對新申請的 API key 回應這兩個模型「no longer available to new users」，所以任何人照 README 重新設定，AI 筆記都會失敗。原本使用的 `google-generativeai` SDK 也已停止支援。

**決策**

- 改用 `google-genai` SDK
- 模型名稱改由環境變數設定：`GEMINI_MODEL`（預設 `gemini-3.6-flash`）、`GEMINI_FALLBACK_MODEL`（預設 `gemini-3.5-flash`）。下次模型退役時，改設定就好，不必改程式
- 主要模型失敗時自動改用備援模型

**驗證（2026-09-24）**

- 把 `GEMINI_MODEL` 設成不存在的名稱 → 主要模型回 404 → 自動改用備援模型並成功回傳
- 端到端測試時遇到主要與備援模型在同一分鐘都回傳 503（Google 端高負載）。SDK 預設不重試，所以對暫時性錯誤（408 / 5xx）補上指數退避重試，重試仍失敗才換備援模型
- 生成 demo 資料時遇到兩種額度限制，兩個模型各自卡在不同的地方：

  | 模型 | 回傳的配額 | 上限 |
  |------|------------|------|
  | `gemini-3.6-flash` | `GenerateRequestsPerDayPerProjectPerModel-FreeTier`（每模型每日請求數） | 20 次 |
  | `gemini-3.5-flash` | `GenerateContentInputTokensPerModelPerMinute-FreeTier`（每模型每分鐘輸入 tokens） | 25 萬 |

  - 額度用完（429）時，對同一模型重試只是在等待；備援模型的額度是分開計算的，所以 429 改成直接換備援模型
  - 備援模型每分鐘 25 萬 tokens 的上限，代表免費方案下太長的影片（例如 136 分鐘那支）只能由主要模型處理，備援模型無法接手
  - 3.6-flash 回傳 429 後，過幾分鐘又能成功呼叫，實際的計算方式與名稱中的「每日」不完全一致，因此不把「每天 20 次」當成確定的規則

---

## 4. 已知問題：摘要存在「每位使用者」那一層

**現況**

資料庫有兩層：

- `videos`：共用的影片快取，同一支影片只存一筆
- `user_videos`：每位使用者自己的狀態（已讀、收藏、筆記）

AI 摘要與中文標題存在 `user_videos`，也就是每位使用者各存一份。

**影響**

同一支影片如果有 N 位使用者點開，就會呼叫 Gemini N 次，產生 N 份內容相近的摘要：

- 成本變成 N 倍（13.6 分鐘的影片約 7.4 萬 tokens）
- 免費方案每天 8 小時的影片額度會被重複消耗
- 每位使用者要各自等待生成

**改善方向（尚未實作）**

- 摘要移到影片層（`videos` 或獨立的 `video_summaries` 表），並記錄生成時使用的模型與 prompt 版本
- `user_videos` 只保留個人狀態
- 第一位使用者觸發生成，之後的使用者直接讀取

目前只有我自己使用，所以沒有立即影響；但這是產品一旦有多位使用者就會放大的成本結構問題，列為下一步。

---

## 5. 影響信任的 Bug 修正

整理作品集時修正的問題。共通點是：功能看似正常，但使用者看到的結果是錯的或難以使用，會直接削弱對產品的信任。

| 問題 | 使用者看到的現象 | 原因 | 修正 |
|------|------------------|------|------|
| 同步永遠顯示 0 部 | 按「同步」後永遠顯示「找到 0 部新影片」，影片列表也不會更新 | API 把同步丟到背景執行，立刻回傳寫死的 `new_videos=0` | 同步在請求內完成並回傳真實數量；頻道並行抓取（上限 5 個）；部分頻道失敗時照實顯示 |
| 摘要沒排版 | AI 筆記顯示成一整塊純文字，沒有標題大小、沒有項目符號 | 使用了 Tailwind 的 `prose` 樣式，但沒安裝 typography 外掛 | 安裝 `@tailwindcss/typography` 並調整深色主題樣式 |
| 通知提示異常 | 提示訊息沒有動畫；多則提示時，前一則的計時會被重置 | 引用了不存在的動畫 class；計時器依賴會變動的值 | 補上動畫；計時器改綁每則提示的 id |
| 手機篩選面板自動關閉 | 在手機上輸入一個字，篩選面板就關掉 | 每次篩選變更都會關閉面板 | 面板保持開啟，直到按「查看結果」、關閉鈕、背景或 Esc |
| 搜尋每打一個字就送出請求 | 輸入時畫面閃爍 | 沒有延遲送出 | 停止輸入 300 毫秒後才搜尋，並在載入時保留上一批結果 |
| 卡片預覽顯示原始 Markdown | 影片卡片出現 `##`、`**` 等符號 | 直接截取摘要原文 | 預覽只取內文、略過段落標題 |
| 返回鍵離開網站 | 從分享連結直接打開影片頁，按「返回」會離開 Brevora | 一律執行瀏覽器上一頁 | 沒有站內上一頁時改回首頁 |
| 時間戳格式不一致 | 有些筆記的時間戳是高亮程式碼樣式，有些是一般文字 | prompt 用反引號示範格式，模型有時照抄 | 移除 prompt 中的反引號；顯示時統一格式 |
