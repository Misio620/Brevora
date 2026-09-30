import { DEMO_MODE, resetDemo } from '@/lib/demoMode'

export default function DemoBanner() {
  if (!DEMO_MODE) return null

  return (
    <div role="note" className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-center text-xs text-amber-200">
      <span className="rounded bg-amber-500/20 px-1.5 py-0.5 font-semibold">Demo 模式</span>
      <span>免登入體驗：筆記是 Gemini 預先生成的真實結果，收藏與已讀只存在你的瀏覽器</span>
      <button onClick={resetDemo} className="text-amber-300 underline underline-offset-2 transition hover:text-amber-100">
        重設
      </button>
    </div>
  )
}
