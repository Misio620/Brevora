"""AI service — generates video notes and translates titles with Google Gemini.

Gemini reads public YouTube videos directly from their URL, so the server never
downloads audio or scrapes captions (YouTube blocks both from cloud hosts).
Model names come from settings because Gemini retires model versions over time.
"""
import logging

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SUMMARY_PROMPT = """請為這支 YouTube 影片生成一份「節目筆記」，同時扮演清楚摘要與閱讀筆記的角色。
嚴格依照以下結構與規則輸出繁體中文 Markdown：

[輸出結構]

## 一句話主題
- 約 20–30 字，說明這支影片在談什麼，以及要解決的核心問題或關鍵主張。
- 不要只重複標題文字，要寫出具體角度或主張。

## 摘要
- 以 2–4 句呈現「這支影片的濃縮內容」，可視為閱讀版摘要。
- 必須同時包含：
  - 背景與目的：針對誰、在什麼情境下有用。
  - 核心結論：講者主要想傳達的結論或關鍵 insight。
- 句子務必具體，避免「很棒、非常實用」等空泛形容詞。

## 五個關鍵要點
- 僅列出 5 點，挑選最重要的五個重點，依影片時間順序排列。
- 每點格式：[mm:ss] 以動詞開頭的重點說明（影片超過一小時用 [h:mm:ss]），時間戳不要加反引號或其他符號。
- 內容聚焦在「方法、步驟、框架、案例或關鍵論點」，而非空泛心得。

## 延伸重點
- 可選，0–5 點。若影片內容較長且有其他值得記錄的次要重點，額外條列補充；沒有就省略整個段落。
- 每點仍以動詞開頭，描述具體做法或觀點。

## 行動呼籲
- 1–3 句，說明觀眾看完這支影片後「可以立刻做什麼」。
- 以動詞開頭，聚焦實際行動。

[通用規則]
- 一律使用繁體中文，專有名詞可保留英文。
- 所有內容必須只根據影片實際內容，不得憑空推測。
- 句子力求短而清楚。
- 優先保留具體概念、步驟、數字與案例。
- 直接輸出筆記，不要加開場白或結語。"""

TRANSLATE_PROMPT = """請將以下 YouTube 影片標題翻譯成繁體中文。
只回傳翻譯後的標題，不要有任何其他說明或符號。

標題：{title}

翻譯："""

_client: genai.Client | None = None
# Model that answered the latest call; informational only (used by the demo data script)
last_model_used: str | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        # The SDK does not retry by default; Gemini often answers 503 during demand spikes.
        # 429 is left out: free-tier quotas are counted per model, so switching to the
        # fallback model is faster than waiting for the same model's quota window.
        _client = genai.Client(
            api_key=settings.GOOGLE_API_KEY,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=4, initial_delay=5, max_delay=60, http_status_codes=[408, 500, 502, 503, 504]
                )
            ),
        )
    return _client


async def _generate(contents, config: types.GenerateContentConfig | None = None) -> str:
    """Calls the primary model, falling back to the secondary one on any error."""
    global last_model_used
    config = config or types.GenerateContentConfig()
    # No tools are used; disabling AFC also silences the SDK's per-call warning
    config.automatic_function_calling = types.AutomaticFunctionCallingConfig(disable=True)
    models = [m for m in dict.fromkeys([settings.GEMINI_MODEL, settings.GEMINI_FALLBACK_MODEL]) if m]
    last_error: Exception | None = None

    for model in models:
        try:
            response = await _get_client().aio.models.generate_content(
                model=model, contents=contents, config=config
            )
            if not response.text:
                raise RuntimeError(f"Empty response from {model}")
            last_model_used = model
            return response.text
        except Exception as e:
            logger.warning(f"Gemini model {model} failed: {e}")
            last_error = e

    raise last_error or RuntimeError("No Gemini model configured")


def _has_cjk(text: str) -> bool:
    return any(
        "一" <= c <= "鿿"
        or "぀" <= c <= "ゟ"
        or "゠" <= c <= "ヿ"
        or "가" <= c <= "힯"
        for c in text
    )


async def generate_summary(video_id: str) -> str:
    """Generates Markdown video notes by letting Gemini watch the YouTube video."""
    logger.info(f"Generating summary for {video_id} with {settings.GEMINI_MODEL}")
    contents = types.Content(
        role="user",
        parts=[
            types.Part(file_data=types.FileData(file_uri=f"https://www.youtube.com/watch?v={video_id}")),
            types.Part(text=SUMMARY_PROMPT),
        ],
    )
    # Low media resolution keeps long podcasts within the context window; notes rely mostly on audio
    config = types.GenerateContentConfig(media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW)
    return (await _generate(contents, config)).strip()


async def translate_title(title: str) -> str | None:
    """Translates a video title to Traditional Chinese. Returns None if it already contains CJK."""
    if _has_cjk(title):
        return None
    translated = (await _generate(TRANSLATE_PROMPT.format(title=title))).strip()
    logger.info(f"Title translation: {title} -> {translated}")
    return translated
