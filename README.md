# Brevora

> 訂閱的 YouTube 影片，先看 AI 節目筆記，再決定要不要看原片。

名字源自拉丁文 *brevis*（簡短）+ *ora*（時間）。

**[線上 Demo（免登入）](DEMO_URL)** · [決策紀錄](docs/decisions.md) · [設計過程](docs/design-process/README.md) · [English](README.en.md)

---

## 問題

我想掌握國外的最新資訊，但遇到三個問題：

- **中文內容不夠即時**：只看中文來源，會比原始資訊慢一步
- **內容多又長，英文不是母語**：訂閱的節目常常讀不完
- **看別人整理的重點，拿到的是二手資訊**：那是別人吸收、篩選過後的版本

原本的做法是每週挑幾個最有興趣的，有時間就看，沒時間就一直放著。

## 我想要的

- **先看重點，再決定要不要深入**：有興趣的再看原片，沒興趣的直接過濾掉。筆記的角色是篩選，不是取代原片
- **資料來源由我決定**：筆記只根據我訂閱的原始影片產生，不經過其他人的整理
- **有輸入也要有輸出**：只有輸入、沒有輸出，不會帶來太多成長。有了筆記，輸入才能更廣也更深

## 產品怎麼運作

1. 用 Google 帳號登入，從 YouTube 訂閱中釘選想追蹤的頻道
2. 同步這些頻道的最新影片
3. 點開影片，Gemini 直接讀取影片內容，生成繁體中文節目筆記：

   | 段落 | 內容 |
   |------|------|
   | 一句話主題 | 影片在談什麼、核心主張是什麼 |
   | 摘要 | 2–4 句，包含適用情境與核心結論 |
   | 五個關鍵要點 | 依影片時間順序排列，每點都附時間戳 |
   | 延伸重點 | 次要但值得記下的內容，沒有就省略 |
   | 行動呼籲 | 看完之後可以立刻做什麼 |

4. 點任一時間戳，就會跳到原片的那一秒，可以查證筆記或深入觀看
5. 用已讀、收藏、頻道、搜尋管理影片

**為什麼筆記是這個結構？** 由我提出需求，和 Claude 討論後定案。五個要點大致就能掌握影片全貌；時間戳可以點回原片，讓筆記的每一點都能回到原始內容確認。

## 使用結果

- 我自己使用了約 1 個月，每週 2–3 次
- 從「有時間才看、沒時間就擱著」，變成每週可以專注吸收 3 個重點，把時間集中在真正有興趣的內容上
- 目前只有我一位使用者，沒有做過其他使用者的研究

## 我的角色

- **產品決策由我主導**：問題定義、功能範圍、筆記結構、部署方式與優先順序
- **程式由 AI（Claude Code）撰寫**；介面的 UX 問題清單也由 Claude 審查產出
- 每個關鍵決策的背景、證據與取捨，都記錄在 [docs/decisions.md](docs/decisions.md)

## 關鍵決策

完整內容見 [決策紀錄](docs/decisions.md)。

1. **作品集用前端 Demo 模式部署，不採用 Supabase**：Supabase 免費專案一週沒有活動就會暫停，而完整版需要 Google 登入，App 通過驗證前只有測試名單上的帳號能登入，面試官無法進入。Demo 模式使用產品本身生成的真實筆記，免登入、不會休眠。
2. **YouTube 封鎖雲端主機，改由 Gemini 直接讀影片網址**：在雲端主機上實測，YouTube 回傳「Sign in to confirm you're not a bot」驗證頁，抓字幕和下載音訊兩條路都會失敗。
3. **Gemini 舊模型退役，模型名稱改為可設定**：加上備援模型與重試；實測時遇到的額度限制（每日請求數、每分鐘 tokens）也一併記錄。
4. **已知問題：摘要存在每位使用者那一層**：同一支影片有 N 位使用者，AI 成本就是 N 倍。已列為下一步。
5. **優先修正會破壞信任的 bug**：例如按「同步」永遠顯示 0 部新影片、AI 筆記沒有排版。

## Demo 說明

- 6 支影片、3 個頻道（How I AI、The Diary Of A CEO、Starter Story），總長 352 分鐘
- 筆記由 [`scripts/generate_demo_data.py`](scripts/generate_demo_data.py) 生成，呼叫的是產品本身的 AI 程式，每支影片都記錄生成時使用的模型。筆記內容沒有人工修改
- 收藏、已讀、釘選頻道都可以操作，資料只存在你的瀏覽器
- Demo 不會連線 YouTube，所以「同步」和「生成新筆記」不會真的執行

## 限制與下一步

- [ ] 摘要改存在影片層，同一支影片只生成一次
- [ ] 安全性修補：JWT 放在網址參數、OAuth 缺少 `state`、密鑰沒有檢查是否仍是預設值、錯誤訊息直接回傳給前端、token 更新後沒有寫回資料庫
- [ ] 自動化測試與 CI
- [ ] 重新設計 Logo 與視覺風格（目前是暫時版本）

## 技術架構

| 層 | 技術 |
|----|------|
| 前端 | React 19、TypeScript、Vite、Tailwind CSS、TanStack Query |
| 後端 | FastAPI、PostgreSQL、SQLAlchemy、Alembic |
| AI | Google Gemini（`google-genai` SDK，直接讀取 YouTube 網址） |
| 外部 API | YouTube Data API v3、Google OAuth 2.0 |
| 部署 | Demo：Vercel（純前端） |

```
瀏覽器 ──> React 前端 ──> FastAPI ──> PostgreSQL
                             ├──> YouTube Data API（訂閱、影片清單）
                             └──> Gemini（YouTube 網址 → 節目筆記）

Demo 模式：React 前端 ──> 瀏覽器內的 demo 層（預先生成的資料 + localStorage）
```

## 本機執行

<details>
<summary>只跑 Demo 模式（不需要後端與 API key）</summary>

```bash
cd frontend
pnpm install
VITE_DEMO_MODE=true pnpm dev
```

開啟 http://localhost:5173

</details>

<details>
<summary>完整版（Google 登入 + 後端）</summary>

需要：Node.js 20+、Python 3.11+、PostgreSQL、pnpm，以及 Google Cloud 專案（YouTube Data API v3 + OAuth 2.0）與 Gemini API key。設定步驟見 [docs/google_setup.md](docs/google_setup.md)。

1. 安裝後端（在專案根目錄執行，會建立 `backend/venv`，Windows / macOS / Linux 都適用）：

   ```bash
   pnpm run install:backend
   cp backend/.env.example backend/.env
   ```

2. 填寫 `backend/.env`：

   | 變數 | 說明 |
   |------|------|
   | `GOOGLE_API_KEY` | Gemini API key（[申請](https://aistudio.google.com/app/apikey)） |
   | `GEMINI_MODEL` | 選填，主要模型，預設 `gemini-3.6-flash` |
   | `GEMINI_FALLBACK_MODEL` | 選填，主要模型失敗時使用，預設 `gemini-3.5-flash` |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth 憑證 |
   | `DATABASE_URL` | PostgreSQL 連線字串 |
   | `JWT_SECRET` | 隨機字串（`python -c "import secrets; print(secrets.token_hex(32))"`） |
   | `ENCRYPTION_KEY` | Fernet key（`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`） |
   | `FRONTEND_URL` / `BACKEND_URL` | `http://localhost:5173` / `http://localhost:8000` |

3. 建立資料表：

   ```bash
   cd backend
   venv/bin/alembic upgrade head   # Windows: venv\Scripts\alembic upgrade head
   ```

4. 建立 `frontend/.env`，內容為 `VITE_API_URL=http://localhost:8000`

5. 在專案根目錄啟動前後端：

   ```bash
   pnpm install
   pnpm dev
   ```

   前端 http://localhost:5173，後端 http://localhost:8000

</details>

<details>
<summary>重新生成 Demo 資料</summary>

需要環境變數 `GOOGLE_API_KEY` 與 `YOUTUBE_API_KEY`（YouTube Data API v3）。

```bash
pnpm run install:backend
backend/venv/bin/python scripts/generate_demo_data.py            # 已完成的影片會跳過
backend/venv/bin/python scripts/generate_demo_data.py --only VIDEO_ID --force
```

Gemini 免費方案有額度限制，中途失敗時直接重跑即可，只會處理還沒完成的影片。

</details>

<details>
<summary>部署 Demo 到 Vercel</summary>

1. 在 Vercel 匯入這個 repo
2. **Root Directory** 設為 `frontend`（Framework 會自動偵測為 Vite）
3. 新增環境變數 `VITE_DEMO_MODE=true`，不需要任何 API key
4. Deploy

</details>

## 專案結構

```
brevora/
├── backend/
│   └── app/
│       ├── routers/        # API：auth、channels、videos
│       ├── services/       # ai.py（Gemini）、youtube.py、encryption.py
│       ├── models/         # SQLAlchemy 資料表
│       └── middleware/     # JWT 驗證
├── frontend/
│   └── src/
│       ├── pages/          # 登入、影片總覽、影片詳細頁
│       ├── components/
│       ├── lib/            # API client、demo 模式
│       └── demo/           # demo 資料（demo-data.json）
├── scripts/
│   ├── backend.mjs              # 跨平台的後端安裝與啟動
│   └── generate_demo_data.py    # 生成 demo 資料
└── docs/
    ├── decisions.md        # 決策紀錄
    ├── design-process/     # Logo 與介面設計過程
    └── google_setup.md     # Google Cloud 設定
```

## License

[MIT](LICENSE)
