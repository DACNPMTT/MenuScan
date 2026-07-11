import { useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Send, Sparkles } from 'lucide-react'
import { apiRequest, ApiError } from '@/shared/lib/api'

interface ChatMsg {
  id: string
  role: 'user' | 'assistant'
  content: string
}

/** Ask-the-assistant chat, grounded on the scanned menu. History is kept only
 * in local state (ephemeral) and a few recent turns are sent for context. */
export function AssistantChat({ menuId }: { menuId: string }) {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async (event: FormEvent) => {
    event.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    const history = messages.slice(-6).map(({ role, content }) => ({ role, content }))
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: question },
    ])
    setInput('')
    setLoading(true)
    try {
      const res = await apiRequest<{ answer: string }>('/api/v1/advisor/chat', {
        method: 'POST',
        body: JSON.stringify({ menu_id: menuId, question, history }),
      })
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content: res.answer },
      ])
    } catch (error) {
      const content =
        error instanceof ApiError && error.status === 429
          ? t('chat.rateLimited')
          : t('chat.error')
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-[8px] border border-hairline bg-canvas p-5">
      <div className="flex items-center gap-2 text-[15px] font-bold text-ink">
        <Sparkles className="size-4 shrink-0 text-primary-dark" aria-hidden />
        {t('chat.title')}
      </div>

      {messages.length === 0 ? (
        <p className="text-[13px] text-ink-variant">{t('chat.hint')}</p>
      ) : (
        <div className="flex max-h-[280px] flex-col gap-2 overflow-y-auto pr-1">
          {messages.map((message) => (
            <div
              key={message.id}
              className={
                message.role === 'user'
                  ? 'max-w-[85%] self-end rounded-[10px] bg-primary-dark px-3 py-2 text-[13px] text-white'
                  : 'max-w-[85%] self-start rounded-[10px] border border-hairline bg-surface-muted px-3 py-2 text-[13px] text-ink'
              }
            >
              {message.content}
            </div>
          ))}
          {loading && (
            <div className="self-start rounded-[10px] border border-hairline bg-surface-muted px-3 py-2 text-ink-variant">
              <Loader2 className="size-4 animate-spin" aria-hidden />
            </div>
          )}
        </div>
      )}

      <form onSubmit={send} className="flex items-center gap-2">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={t('chat.placeholder')}
          className="min-h-10 flex-1 rounded-[8px] border border-hairline bg-white px-3 text-[14px] text-ink outline-none focus:border-primary-dark"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          aria-label={t('chat.send')}
          className="flex size-10 shrink-0 items-center justify-center rounded-[8px] bg-primary-dark text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send className="size-4" aria-hidden />
        </button>
      </form>

      <p className="text-[11px] text-ink-variant">{t('chat.disclaimer')}</p>
    </section>
  )
}
