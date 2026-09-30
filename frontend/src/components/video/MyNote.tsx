import { useEffect, useRef, useState } from 'react'
import { NOTE_MAX_LENGTH, useSaveNote } from '@/hooks/useVideos'

const SAVE_DELAY_MS = 1000

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface MyNoteProps {
  youtubeId: string
  initialNote: string
}

// The viewer's own note: autosaves 1s after typing stops, one request at a time, always the latest text
export default function MyNote({ youtubeId, initialNote }: MyNoteProps) {
  const [text, setText] = useState(initialNote)
  const [status, setStatus] = useState<SaveStatus>('idle')
  const { mutateAsync } = useSaveNote()

  const latestRef = useRef(initialNote) // what the editor holds now
  const savedRef = useRef(initialNote) // what the server has confirmed
  const inFlightRef = useRef(false)
  const timerRef = useRef<number | undefined>(undefined)

  const flush = async () => {
    window.clearTimeout(timerRef.current)
    // The request in flight checks again when it finishes
    if (inFlightRef.current) return
    const note = latestRef.current
    if (note === savedRef.current) return

    inFlightRef.current = true
    setStatus('saving')
    try {
      await mutateAsync({ youtubeId, note })
      savedRef.current = note
    } catch {
      inFlightRef.current = false
      setStatus('error')
      return
    }
    inFlightRef.current = false
    // Typed while saving: save the newer text next
    if (latestRef.current !== savedRef.current) void flush()
    else setStatus('saved')
  }

  const flushRef = useRef(flush)
  flushRef.current = flush

  // Save pending text when leaving the page; warn before closing the tab with unsaved text
  useEffect(() => {
    const warnIfUnsaved = (e: BeforeUnloadEvent) => {
      if (latestRef.current !== savedRef.current) e.preventDefault()
    }
    window.addEventListener('beforeunload', warnIfUnsaved)
    return () => {
      window.removeEventListener('beforeunload', warnIfUnsaved)
      void flushRef.current()
    }
  }, [])

  const handleChange = (value: string) => {
    setText(value)
    latestRef.current = value
    window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(() => void flushRef.current(), SAVE_DELAY_MS)
  }

  return (
    <section className="glass-card-strong mt-6 rounded-xl border border-slate-700/50 p-6">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="my-note-heading" className="text-base font-semibold text-slate-200">我的筆記</h2>
        <div aria-live="polite" className="text-xs">
          {status === 'saving' && <span className="text-slate-400">儲存中…</span>}
          {status === 'saved' && <span className="text-emerald-400">已儲存</span>}
          {status === 'error' && (
            <span className="flex items-center gap-2 text-red-400">
              儲存失敗
              <button
                onClick={() => void flush()}
                className="rounded bg-red-500/10 px-2 py-0.5 font-medium text-red-300 transition hover:bg-red-500/20"
              >
                重試
              </button>
            </span>
          )}
        </div>
      </div>
      <textarea
        aria-labelledby="my-note-heading"
        value={text}
        onChange={e => handleChange(e.target.value)}
        onBlur={() => void flush()}
        maxLength={NOTE_MAX_LENGTH}
        rows={6}
        placeholder="這支影片讓你想到什麼？打算做什麼？"
        className="glass-input w-full resize-y rounded-lg border border-slate-700 px-3 py-2 text-sm leading-relaxed text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20"
      />
      <div className="mt-1.5 flex justify-between text-xs text-slate-500">
        <span>只有你看得到，停止輸入 1 秒後自動儲存</span>
        <span>{text.length.toLocaleString()} / {NOTE_MAX_LENGTH.toLocaleString()}</span>
      </div>
    </section>
  )
}
