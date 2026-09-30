# Google Cloud 設定

Brevora 需要兩組 Google 憑證：

- **OAuth Client**：讓使用者登入並讀取 YouTube 訂閱（`GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`）
- **Gemini API Key**：生成節目筆記（`GOOGLE_API_KEY`）

## 1. 建立專案並啟用 API

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)，建立新專案。
2. **APIs & Services → Library**，搜尋並啟用 **YouTube Data API v3**。

## 2. 設定 OAuth 同意畫面

1. **APIs & Services → OAuth consent screen**，User Type 選 **External**。
2. 填入 App name 與聯絡 email。
3. Scopes 加入 `.../auth/youtube.readonly`。
4. Test users 加入要登入的 Google 帳號。

> `youtube.readonly` 屬於敏感範圍。App 未通過 Google 驗證前，只有 Test users 名單內的帳號能登入。

## 3. 建立 OAuth Client

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**。
2. Application type 選 **Web application**。
3. **Authorized redirect URIs** 加入：
   ```
   http://localhost:8000/auth/google/callback
   ```
   部署後再加入正式網址的 `<BACKEND_URL>/auth/google/callback`。
4. 將 Client ID 與 Client Secret 填入 `backend/.env`。

## 4. 取得 Gemini API Key

到 [Google AI Studio](https://aistudio.google.com/app/apikey) 建立 API key，填入 `backend/.env` 的 `GOOGLE_API_KEY`。
