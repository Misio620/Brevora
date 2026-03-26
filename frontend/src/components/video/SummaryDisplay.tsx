import Markdown from 'react-markdown'

interface SummaryDisplayProps {
  summary: string
}

export default function SummaryDisplay({ summary }: SummaryDisplayProps) {
  return (
    <div className="prose prose-sm max-w-none text-slate-300 prose-headings:text-slate-100 prose-strong:text-slate-200 prose-li:my-0.5 prose-a:text-blue-400 prose-a:underline prose-a:underline-offset-2 hover:prose-a:text-blue-300">
      <Markdown>{summary}</Markdown>
    </div>
  )
}
