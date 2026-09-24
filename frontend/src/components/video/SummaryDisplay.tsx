import Markdown from 'react-markdown'

interface SummaryDisplayProps {
  summary: string
}

export default function SummaryDisplay({ summary }: SummaryDisplayProps) {
  return (
    <div className="prose prose-sm prose-invert max-w-none prose-p:text-slate-300 prose-li:text-slate-300 prose-li:my-0.5 prose-headings:text-slate-100 prose-strong:text-slate-100 prose-a:text-blue-400 prose-a:underline-offset-2 hover:prose-a:text-blue-300 prose-code:text-blue-300 prose-code:before:content-none prose-code:after:content-none">
      <Markdown>{summary}</Markdown>
    </div>
  )
}
