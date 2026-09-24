# Brevora

> AI-powered YouTube video digest — grasp key insights from your subscriptions in minutes.

Brevora 讓你快速掌握 YouTube 訂閱影片的重點，不再為「看不完」而焦慮。
名字源自拉丁文 *brevis*（簡短）+ *ora*（時間）。

---

## Features

- **Google OAuth** — 一鍵登入，自動同步 YouTube 訂閱
- **AI Summary** — 使用 Google Gemini 自動生成影片節目筆記
- **Dashboard** — 依狀態、頻道、收藏篩選影片
- **Responsive** — 桌面與行動裝置皆可使用
- **Dark Theme** — 毛玻璃風格深色介面

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI, PostgreSQL, SQLAlchemy, Alembic |
| AI | Google Gemini API |
| Auth | Google OAuth 2.0, JWT |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL
- pnpm
- Google Cloud project with YouTube Data API v3 + OAuth 2.0 credentials
- Google Gemini API key

### 1. Clone

```bash
git clone https://github.com/Misio620/brevora.git
cd brevora
```

### 2. Backend Setup

From the project root (creates `backend/venv` and installs dependencies, works on Windows / macOS / Linux):

```bash
pnpm run install:backend
```

Copy and fill in environment variables (see [docs/google_setup.md](docs/google_setup.md) for Google credentials):

```bash
cp backend/.env.example backend/.env
```

Required variables in `backend/.env`:

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Gemini API key ([Get one](https://aistudio.google.com/app/apikey)) |
| `GEMINI_MODEL` | Optional. Primary model, default `gemini-3.6-flash` |
| `GEMINI_FALLBACK_MODEL` | Optional. Used when the primary model fails, default `gemini-3.5-flash` |
| `GOOGLE_CLIENT_ID` | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Random hex string (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ENCRYPTION_KEY` | Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `FRONTEND_URL` | `http://localhost:5173` |
| `BACKEND_URL` | `http://localhost:8000` |

Run database migration (with `backend/venv` activated):

```bash
cd backend
alembic upgrade head
```

### 3. Frontend Setup

```bash
cd frontend
pnpm install
```

Create `frontend/.env`:

```
VITE_API_URL=http://localhost:8000
```

### 4. Run

From the project root:

```bash
pnpm install
pnpm dev
```

This starts both frontend (http://localhost:5173) and backend (http://localhost:8000) concurrently.

## Project Structure

```
brevora/
├── backend/
│   ├── app/
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routers/       # API endpoints (auth, videos, channels)
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # AI & YouTube services
│   │   └── middleware/     # Auth middleware
│   ├── alembic/           # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/         # LoginPage, DashboardPage, VideoDetailPage
│   │   ├── components/    # Layout, Video, Channel, Common components
│   │   ├── hooks/         # useAuth, useVideos, useChannels
│   │   └── lib/           # API client, auth helpers
│   └── index.html
└── package.json           # Root scripts (pnpm dev)
```

## License

[MIT](LICENSE)
