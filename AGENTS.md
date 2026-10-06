# AGENTS.md — Brevora

> 全域指令：Codex 見 `~/.codex/AGENTS.md`，Claude Code 見 `~/.claude/CLAUDE.md`（匯入前者）。
> 安裝、環境變數、技術棧、專案結構見 `README.md`，此檔不重複。

## 狀態

**進行中**（2026-10-01 更新）。

## 協作流程

本機與雲端 session 共用 GitHub 的 `main`：
- 不直接推 `main`：從最新的 `origin/main` 開分支 → 開 PR → 使用者合併。一個 PR 只做一件事，拆成小 commit。本機無法開 PR 時，推分支後請使用者在 GitHub 開。
- PR 描述寫：改了什麼、為什麼、怎麼驗證（沒驗證的要寫明）。
- PR 要等 CI（`.github/workflows/ci.yml`）通過才合併；改到後端行為時，在 `backend/tests/` 補上或更新測試。
- 需要使用者資料庫、Google 登入或瀏覽器實測的工作在本機做，其餘可在雲端做；兩邊不同時改同一個檔案。
- 新 PR 依賴另一個還沒合併的 PR 時，從那個 PR 的分支開分支、base 設為它，描述第一行寫明依賴哪個 PR。repo 已開啟合併後自動刪除分支，底層 PR 合併後上層 PR 的 base 會自動改成 `main`；合併上層 PR 前仍確認 base 是 `main`（#14 曾因 base 沒改而合併進舊分支）。

## 品牌視覺

- 底色：`#0f172a`（深色主題）
- 字體：Instrument Serif（italic）標題 + DM Sans 內文
- Accent：`#2563EB`
- Logo：暫不使用圖示，純文字 wordmark + shimmer 動畫；favicon 為 Instrument Serif 斜體字母「B」（`frontend/public/favicon.svg`）

## CSS 慣例

毛玻璃樣式統一定義在 `frontend/src/index.css`：

```
glass-card / glass-card-strong / glass-nav / glass-sidebar / glass-modal / glass-input
video-card   ← VideoCard 專用 hover/focus
```

全部支援 `prefers-reduced-motion`。**新增元件沿用這些 class，不要另外寫毛玻璃樣式。**

## Port

frontend 5173（`strictPort: true`）、backend 8000（2026-09-30 從 8002 統一為上游的 8000）。
根目錄 `pnpm dev` 一鍵啟動，`predev` 只檢查這兩個 port 是否可用；被占用時停止啟動並回報，不關閉任何行程。
Google OAuth 的 redirect_uri 由 `backend/.env` 的 `BACKEND_URL` 組成（`backend/app/routers/auth.py`），本機為 `localhost:8000`；Google Cloud Console 目前同時登記 8000 與 8002 兩個 callback（使用者 2026-09-30 告知）。處理登入問題時仍需實際核對。

**保留 `strictPort: true`。** 固定連接埠是為了維持前後端、API URL 與登入回呼的一致性。現行後端在 localhost 設定下允許鄰近 CORS port，不能再把「fallback 一定被 CORS 擋下」當成普遍原因；CORS／OAuth 問題依實際設定查核。
保留 predev 占用檢查與 strictPort。若需停止既有行程，先確認 PID 屬於本次任務管理、可安全停止的 Brevora 行程；其他占用應回報阻塞。

套件管理用 **pnpm**（2026-03-20 從 npm 轉換），不要混用 npm。

## 待辦

- [x] Google OAuth 同意畫面名稱改成 Brevora（2026-09-30 使用者完成）
- [ ] 部署上線時設定後端 log 輸出到檔案

## 相依套件

- `backend/requirements.txt` 以 `==` 鎖定直接依賴（2026-09-30），版本為實測 Google 登入、同步影片、
  顯示既有筆記與產生 AI 筆記皆正常的組合；間接依賴未鎖定。
- 升級套件時手動改版本號，並重新實測上述流程，不要改回 `>=`。
