# 如何取得 Google Cloud Project 憑證 (`client_secret.json`)

為了讓應用程式能讀取您的 YouTube 訂閱內容，您需要建立一個 Google Cloud 專案並啟用 API。請按照以下步驟操作：

## 步驟 1：建立專案
1.  前往 [Google Cloud Console](https://console.cloud.google.com/)。
2.  點擊左上角的專案選單，選擇 **"New Project" (新增專案)**。
3.  輸入專案名稱 (例如 `YouTube-AI-Reader`)，點擊 **"Create" (建立)**。

## 步驟 2：啟用 YouTube Data API
1.  在左側選單中，點擊 **"APIs & Services" (API 和服務)** > **"Library" (程式庫)**。
2.  在搜尋框輸入 `YouTube Data API v3`。
3.  點擊搜尋結果，然後點擊 **"Enable" (啟用)**。

## 步驟 3：設定 OAuth 同意畫面 (OAuth Consent Screen)
1.  前往 **"APIs & Services"** > **"OAuth consent screen" (OAuth 同意畫面)**。
2.  **User Type (使用者類型)** 選擇 **"External" (外部)** (除非您有 Google Workspace 組織)，點擊 **"Create"**。
3.  **App Information**：
    *   App name: `YouTube Reader` (或您喜歡的名字)
    *   User support email: 選擇您的 Email
    *   Developer contact information: 輸入您的 Email
4.  點擊 **"Save and Continue"**。
5.  **Scopes (範圍)**：點擊 **"Add or Remove Scopes"**，搜尋並勾選 `.../auth/youtube.readonly` (這允許我們讀取您的訂閱)，然後點擊 **"Update"**。
6.  **Test Users (測試使用者)**：
    *   因為應用程式尚未發布，您必須將自己的 Email 加入測試名單。
    *   點擊 **"Add Users"**，輸入您的 Google Email，點擊 **"Save"**。

## 步驟 4：建立憑證 (Credentials)
1.  前往 **"APIs & Services"** > **"Credentials" (憑證)**。
2.  點擊上方 **"Create Credentials"** > **"OAuth client ID"**。
3.  **Application type** 選擇 **"Desktop app" (桌面應用程式)**。
4.  Name 輸入 `Desktop Client`，點擊 **"Create"**。
5.  建立成功後，會跳出一個視窗。點擊 **"DOWNLOAD JSON"** 下載檔案。
6.  將下載的檔案重新命名為 `client_secret.json`，並妥善保存。

> [!IMPORTANT]
> 這個 `client_secret.json` 檔案等同於應用程式的鑰匙，請勿分享給他人。稍後我們會將其放入應用程式的設定資料夾中。
