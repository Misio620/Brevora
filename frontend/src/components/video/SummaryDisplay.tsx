import Markdown from 'react-markdown'

// [mm:ss] or [h:mm:ss], optionally wrapped in backticks by older notes, and not already a link
const TIMESTAMP = /`?\[((?:\d{1,2}:)?\d{1,2}:\d{2})\]`?(?!\()/g

function toSeconds(timestamp: string): number {
  return timestamp.split(':').reduce((total, part) => total * 60 + Number(part), 0)
}

// Turns each timestamp into a link that opens the video at that moment, so a note can be checked against the source
function linkTimestamps(summary: string, youtubeId: string): string {
  return summary.replace(
    TIMESTAMP,
    (_, timestamp: string) => `[${timestamp}](https://www.youtube.com/watch?v=${youtubeId}&t=${toSeconds(timestamp)}s)`,
  )
}

interface SummaryDisplayProps {
  summary: string
  youtubeId: string
}

export default function SummaryDisplay({ summary, youtubeId }: SummaryDisplayProps) {
  return (
    <div className="prose prose-sm prose-invert max-w-none prose-p:text-slate-300 prose-li:text-slate-300 prose-li:my-0.5 prose-headings:text-slate-100 prose-strong:text-slate-100 prose-a:text-blue-400 prose-a:underline-offset-2 hover:prose-a:text-blue-300 prose-code:text-blue-300 prose-code:before:content-none prose-code:after:content-none">
      <Markdown
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="font-mono tabular-nums">
              {children}
            </a>
          ),
        }}
      >
        {linkTimestamps(summary, youtubeId)}
      </Markdown>
    </div>
  )
}
