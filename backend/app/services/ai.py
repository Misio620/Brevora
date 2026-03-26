"""AI service — generates summaries and translates titles using Google Gemini.

Preserved from the original backend/services/ai.py with these changes:
- Made async via asyncio.to_thread
- Uses Python logging instead of file-based ai_debug.log
- Config from pydantic-settings instead of module-level load_dotenv
- Removed duplicate download_audio (consolidated here)
"""
import asyncio
import logging
import os
import tempfile

import google.generativeai as genai
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

DOWNLOAD_DIR = tempfile.mkdtemp(prefix="yt_reader_")


def _translate_title(title: str) -> str | None:
    """Translates English video title to Traditional Chinese. Returns None if already CJK."""
    has_cjk = any(
        "\u4e00" <= c <= "\u9fff"
        or "\u3040" <= c <= "\u309f"
        or "\u30a0" <= c <= "\u30ff"
        or "\uac00" <= c <= "\ud7af"
        for c in title
    )

    if has_cjk:
        return None

    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""請將以下 YouTube 影片標題翻譯成繁體中文。
只回傳翻譯後的標題，不要有任何其他說明或符號。

標題：{title}

翻譯："""

    response = model.generate_content(prompt)
    translated = response.text.strip()
    logger.info(f"Title translation: {title} -> {translated}")
    return translated


def _get_transcript(video_id: str) -> str | None:
    """Gets the transcript/captions for a YouTube video."""
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)

        try:
            transcript = transcript_list.find_transcript(["zh-Hant", "zh-TW", "zh", "en"])
        except Exception:
            transcript = transcript_list[0]

        transcript_data = transcript.fetch()
        return " ".join([entry.text for entry in transcript_data])
    except Exception as e:
        logger.warning(f"Transcript error for {video_id}: {e}")
        return None


def _download_audio(video_id: str) -> str:
    """Downloads the audio of a YouTube video. Returns file path."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")

    # Clean up existing files
    for filename in os.listdir(DOWNLOAD_DIR):
        if filename.startswith(video_id):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, filename))
            except Exception:
                pass

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "no_continue": True,
        "overwrites": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            return os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    except Exception:
        # Fallback: try without conversion
        ydl_opts.pop("postprocessors")
        ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info["ext"]
            return os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")


SUMMARY_PROMPT = """請為以下 YouTube 影片的逐字稿生成一份「節目筆記」，同時扮演清楚摘要與閱讀筆記的角色。
嚴格依照以下結構與規則輸出繁體中文：

[輸出結構]

1. 一句話主題（One-liner）
- 約 20–30 字，說明這支影片在談什麼，以及要解決的核心問題或關鍵主張。
- 不要只重複標題文字，要寫出具體角度或主張。

2. 摘要段落
- 以 2–4 句呈現「這支影片的濃縮內容」，可視為閱讀版摘要。
- 必須同時包含：
  - 背景與目的：針對誰、在什麼情境下有用。
  - 核心結論：講者主要想傳達的結論或關鍵 insight。
- 句子務必具體，避免「很棒、非常實用」等空泛形容詞。

3. 五個關鍵要點（含時間軸）
- 僅列出 5 點，挑選最重要的五個重點。
- 每點格式：`[mm:ss] 以動詞開頭的重點說明` (若逐字稿無時間碼則省略時間)
- 內容聚焦在「方法、步驟、框架、案例或關鍵論點」，而非空泛心得。

4. 延伸重點條列（可選，0–5 點）
- 若影片內容較長且有其他值得記錄的次要重點，額外條列 0–5 點補充。
- 每點仍以動詞開頭，描述具體做法或觀點。

5. 行動呼籲（Call to action）
- 1–3 句，說明觀眾看完這支影片後「可以立刻做什麼」。
- 以動詞開頭，聚焦實際行動。

[通用規則]
- 一律使用繁體中文。
- 所有內容必須只根據影片實際內容，不得憑空推測。
- 句子力求短而清楚。
- 優先保留具體概念、步驟、數字與案例。

逐字稿：
"""

AUDIO_SUMMARY_PROMPT = """請為這個 YouTube 影片生成一份「節目筆記」，同時扮演清楚摘要與閱讀筆記的角色。
嚴格依照以下結構與規則輸出繁體中文：

[輸出結構]

1. 一句話主題（One-liner）
- 約 20–30 字，說明這支影片在談什麼，以及要解決的核心問題或關鍵主張。
- 不要只重複標題文字，要寫出具體角度或主張。

2. 摘要段落
- 以 2–4 句呈現「這支影片的濃縮內容」，可視為閱讀版摘要。
- 必須同時包含：
  - 背景與目的：針對誰、在什麼情境下有用。
  - 核心結論：講者主要想傳達的結論或關鍵 insight。
- 句子務必具體，避免「很棒、非常實用」等空泛形容詞。

3. 五個關鍵要點
- 僅列出 5 點，挑選最重要的五個重點。
- 每點格式：`以動詞開頭的重點說明`
- 內容聚焦在「方法、步驟、框架、案例或關鍵論點」，而非空泛心得。

4. 延伸重點條列（可選，0–5 點）
- 若影片內容較長且有其他值得記錄的次要重點，額外條列 0–5 點補充。
- 每點仍以動詞開頭，描述具體做法或觀點。

5. 行動呼籲（Call to action）
- 1–3 句，說明觀眾看完這支影片後「可以立刻做什麼」。
- 以動詞開頭，聚焦實際行動。

[通用規則]
- 一律使用繁體中文。
- 所有內容必須只根據影片實際內容，不得憑空推測。
- 句子力求短而清楚。
- 優先保留具體概念、步驟、數字與案例。

請用繁體中文回應："""


def _generate_summary_from_transcript(transcript: str) -> str:
    """Generates a summary from a transcript text."""
    logger.info("Using transcript for summary generation...")
    model = genai.GenerativeModel("gemini-2.5-flash")
    full_prompt = SUMMARY_PROMPT + transcript[:25000] + "\n\n請用繁體中文回應："

    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        logger.warning(f"Primary model error: {e}, falling back to gemini-2.5-flash-lite")
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        response = model.generate_content(full_prompt)
        return response.text


def _generate_summary_from_audio(video_id: str) -> str:
    """Generates a summary from audio (fallback method)."""
    import time

    audio_path = _download_audio(video_id)
    logger.info(f"Uploading audio for {video_id} to Gemini...")
    audio_file = genai.upload_file(path=audio_path)

    while audio_file.state.name == "PROCESSING":
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)

    if audio_file.state.name == "FAILED":
        raise Exception(f"File upload failed with state: {audio_file.state.name}")

    model = genai.GenerativeModel("gemini-2.5-flash")

    try:
        response = model.generate_content([audio_file, AUDIO_SUMMARY_PROMPT])
    except Exception as e:
        logger.warning(f"Primary model error for audio: {e}, falling back to gemini-2.5-flash-lite")
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        response = model.generate_content([audio_file, AUDIO_SUMMARY_PROMPT])
    finally:
        # Cleanup
        try:
            genai.delete_file(audio_file.name)
        except Exception:
            pass
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

    return response.text


def _generate_summary(video_id: str) -> str:
    """Main function: transcript first, audio fallback."""
    logger.info(f"Generating summary for {video_id}...")
    transcript = _get_transcript(video_id)

    if transcript and len(transcript) > 100:
        logger.info(f"Transcript found for {video_id}, using transcript method")
        return _generate_summary_from_transcript(transcript)

    logger.info(f"No transcript for {video_id}, falling back to audio method")
    return _generate_summary_from_audio(video_id)


# Async public API
async def generate_summary(video_id: str) -> str:
    return await asyncio.to_thread(_generate_summary, video_id)


async def translate_title(title: str) -> str | None:
    return await asyncio.to_thread(_translate_title, title)


async def get_transcript(video_id: str) -> str | None:
    return await asyncio.to_thread(_get_transcript, video_id)
