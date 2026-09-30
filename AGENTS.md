# AGENTS.md — Brevora

> 全域指令：Codex 見 `~/.codex/AGENTS.md`，Claude Code 見 `~/.claude/CLAUDE.md`（匯入前者）。
> 安裝、環境變數、技術棧、專案結構見 `README.md`，此檔不重複。

## 狀態

**進行中**（2026-09-30 更新）。

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

- [ ] Google OAuth 同意畫面名稱需到 Google Cloud Console 手動改成 Brevora
- [ ] 部署上線時設定後端 log 輸出到檔案

## 已知問題

- **`requirements.txt` 只設下限（`>=`）**：重建 venv 會裝到最新版。2026-09-30 重建時升到
  SQLAlchemy 2.1、Starlette 1.x、protobuf 7；2026-09-30 已實測 Google 登入、同步影片、顯示既有筆記與產生 AI 筆記皆正常。
  日後重建若出現相依套件錯誤，先比對版本，必要時再討論是否鎖定版本。
