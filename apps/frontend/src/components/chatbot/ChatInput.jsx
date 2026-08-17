import { useRef, useState, useEffect } from 'react'
import { SendHorizontal, Loader2 } from 'lucide-react'

const SUGGESTED_PROMPTS = [
  'Payment API is returning HTTP 401',
  'Why did this happen?',
  'Which file should I fix?',
  'Have we seen this issue before?',
  'How can I prevent this?',
]

// Suggestions are prompt starters only — never used as mock data.
export default function ChatInput({ onSend, sending, prefill }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  useEffect(() => {
    if (prefill) setValue(prefill)
  }, [prefill])

  function handleSend() {
    const trimmed = value.trim()
    if (!trimmed || sending) return
    onSend(trimmed)
    setValue('')
    textareaRef.current?.focus()
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-border-subtle bg-bg-panel/60 backdrop-blur-sm px-4 py-3 space-y-2.5">
      <div className="flex flex-wrap gap-1.5">
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => setValue(prompt)}
            disabled={sending}
            className="text-[11px] px-2.5 py-1 rounded-full border border-border-subtle text-ink-muted hover:text-accent-cyan hover:border-accent-cyan/40 transition-colors disabled:opacity-50"
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className="flex items-end gap-2.5">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Describe your incident or ask a question…"
          className="flex-1 resize-none rounded-xl bg-bg-base/60 border border-border px-3.5 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted focus:border-accent-cyan/50 outline-none max-h-32"
        />
        <button
          onClick={handleSend}
          disabled={!value.trim() || sending}
          className="shrink-0 inline-flex items-center justify-center w-10 h-10 rounded-xl bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 hover:bg-accent-cyan/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {sending ? <Loader2 size={16} className="animate-spin" /> : <SendHorizontal size={16} />}
        </button>
      </div>
    </div>
  )
}
