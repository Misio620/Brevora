import os
import yt_dlp
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
import traceback

load_dotenv()

GENAI_API_KEY = os.getenv("GOOGLE_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'downloads')
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def translate_title(title):
    """Translates English video title to Traditional Chinese."""
    try:
        # Check if title contains ANY CJK characters (Situation B)
        # CJK Unified Ideographs: 4E00-9FFF
        # Hiragana: 3040-309F
        # Katakana: 30A0-30FF
        # Hangul: AC00-D7AF
        has_cjk = any(
            '\u4e00' <= c <= '\u9fff' or
            '\u3040' <= c <= '\u309f' or
            '\u30a0' <= c <= '\u30ff' or
            '\uac00' <= c <= '\ud7af'
            for c in title
        )
        
        if has_cjk:
            # Situation B: Title contains CJK, do not translate
            return None
            
        # Situation A: Pure English title, translate
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = f"""請將以下 YouTube 影片標題翻譯成繁體中文。
只回傳翻譯後的標題，不要有任何其他說明或符號。

標題：{title}

翻譯："""
        
        response = model.generate_content(prompt)
        translated = response.text.strip()
        print(f"Title translation: {title} -> {translated}")
        return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return None

def get_transcript(video_id):
    """Gets the transcript/captions for a YouTube video."""
    try:
        # Get transcript list
        transcript_list = YouTubeTranscriptApi().list(video_id)
        
        # Try to find transcript in preferred languages
        try:
            transcript = transcript_list.find_transcript(['zh-Hant', 'zh-TW', 'zh', 'en'])
        except:
            # Get first available transcript
            transcript = transcript_list[0]
        
        # Fetch and combine text
        transcript_data = transcript.fetch()
        return ' '.join([entry.text for entry in transcript_data])
    except Exception as e:
        print(f"Transcript error: {e}")
        return None

def download_audio(video_id):
    """Downloads the audio of a YouTube video."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")
    
    # Path to local ffmpeg
    BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
    FFMPEG_DIR = os.path.join(BACKEND_DIR, 'bin')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'ffmpeg_location': FFMPEG_DIR,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'no_continue': True,  # Do not resume partially downloaded files (fixes 416 error)
        'overwrites': True,   # Overwrite existing files
    }
    
    print(f"Downloading audio for {video_id}...")
    
    # Aggressive cleanup: Delete any existing files for this video ID to prevent 416 Resume errors
    try:
        for filename in os.listdir(DOWNLOAD_DIR):
            if filename.startswith(video_id):
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                try:
                    os.remove(file_path)
                    print(f"Deleted existing file: {file_path}")
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")
    except Exception as e:
        print(f"Cleanup error: {e}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            return os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    except Exception:
        # Try without conversion (might be m4a or webm)
        ydl_opts.pop('postprocessors')
        ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info['ext']
            return os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")

def generate_summary_from_transcript(transcript):
    """Generates a summary from a transcript."""
    print("Using transcript for summary generation...")
    
    # Try experimental model first, fallback to stable
    model_name = 'gemini-2.0-flash-exp'
    
    prompt_base = """請為以下 YouTube 影片的逐字稿生成一份「節目筆記」，同時扮演清楚摘要與閱讀筆記的角色。
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
    # Use concatenation to avoid f-string errors with braces in transcript
    full_prompt = prompt_base + transcript[:25000] + "\n\n請用繁體中文回應："
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        # Log to file
        with open('ai_debug.log', 'a', encoding='utf-8') as f:
            f.write(f"Transcript Summary Error ({model_name}): {str(e)}\n")
            
        print(f"Error with primary model {model_name}: {e}")
        print("Falling back to gemini-1.5-flash...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt)
        return response.text

def generate_summary_from_audio(video_id):
    """Generates a summary from audio (fallback method)."""
    # Download audio
    audio_path = download_audio(video_id)
    
    print("Uploading to Gemini...")
    audio_file = genai.upload_file(path=audio_path)
    
    print("Waiting for audio processing...")
    while audio_file.state.name == "PROCESSING":
        import time
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)
    
    if audio_file.state.name == "FAILED":
        raise Exception(f"File upload failed with state: {audio_file.state.name}")
    
    print("Generating summary from audio...")
    
    # Try experimental model first, fallback to stable
    model_name = 'gemini-2.0-flash-exp'
    
    prompt = """請為這個 YouTube 影片生成一份「節目筆記」，同時扮演清楚摘要與閱讀筆記的角色。
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
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([audio_file, prompt])
        
        # Cleanup
        try:
            genai.delete_file(audio_file.name)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            print(f"Cleanup warning: {e}")
            
        return response.text
    except Exception as e:
        # Log to file
        with open('ai_debug.log', 'a', encoding='utf-8') as f:
            f.write(f"Audio Summary Error ({model_name}): {str(e)}\n")
            
        print(f"Error with primary model {model_name} for audio: {e}")
        print("Falling back to gemini-1.5-flash...")
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([audio_file, prompt])
            
            # Cleanup
            try:
                genai.delete_file(audio_file.name)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                print(f"Cleanup warning: {e}")
                
            return response.text
        except Exception as fallback_error:
            # Log fallback error
            with open('ai_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"Audio Summary Fallback Error: {str(fallback_error)}\n")
                
            # If fallback also fails, ensure cleanup happens
            try:
                genai.delete_file(audio_file.name)
            except:
                pass
            raise fallback_error

def generate_summary(video_id):
    """Main function to generate summary (transcript first, audio fallback)."""
    try:
        print(f"Attempting to get transcript for {video_id}...")
        transcript = get_transcript(video_id)
        
        if transcript and len(transcript) > 100:
            print("[OK] Transcript found! Generating summary...")
            return generate_summary_from_transcript(transcript)

        # Method 2: Fallback to audio (slower)
        print("[WARN] No transcript available. Falling back to audio method...")
        return generate_summary_from_audio(video_id)
        
    except Exception as e:
        # Log top-level error (including download failures)
        with open('ai_debug.log', 'a', encoding='utf-8') as f:
            f.write(f"Top Level AI Error: {str(e)}\nTraceback: {traceback.format_exc()}\n")
            
        print(f"AI Error: {e}")
        raise e
