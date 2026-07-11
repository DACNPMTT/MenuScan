import { useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Bot, Loader2, Send, X } from 'lucide-react'
import { apiRequest, ApiError } from '@/shared/lib/api'

interface ChatMsg {
  id: string
  role: 'user' | 'assistant'
  content: string
}

/** Floating assistant: a fixed bot button (always visible while scrolling) that
 * toggles a chat panel. Grounded on the scanned menu; history is kept only in
 * local state (ephemeral) and a few recent turns are sent for context. */
export function AssistantChat({ menuId }: { menuId: string }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
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
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3">
      {open && (
        <div className="flex max-h-[70vh] w-[min(92vw,380px)] flex-col overflow-hidden rounded-[14px] border border-hairline bg-canvas shadow-[0_12px_40px_rgba(15,23,42,0.18)]">
          <div className="flex items-center justify-between gap-2 border-b border-hairline bg-surface-muted px-4 py-3">
            <div className="flex items-center gap-2 text-[14px] font-bold text-ink">
              <Bot className="size-4 shrink-0 text-primary-dark" aria-hidden />
              {t('chat.title')}
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label={t('common.close')}
              className="flex size-7 items-center justify-center rounded-[8px] text-ink-variant transition-colors hover:bg-canvas"
            >
              <X className="size-4" aria-hidden />
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-2 overflow-y-auto px-4 py-3">
            {messages.length === 0 ? (
              <p className="text-[13px] text-ink-variant">{t('chat.hint')}</p>
            ) : (
              messages.map((message) => (
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
              ))
            )}
            {loading && (
              <div className="self-start rounded-[10px] border border-hairline bg-surface-muted px-3 py-2 text-ink-variant">
                <Loader2 className="size-4 animate-spin" aria-hidden />
              </div>
            )}
          </div>

          <form
            onSubmit={send}
            className="flex items-center gap-2 border-t border-hairline px-3 py-3"
          >
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

          <p className="border-t border-hairline px-4 py-2 text-[11px] text-ink-variant">
            {t('chat.disclaimer')}
          </p>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={t('chat.title')}
        aria-expanded={open}
        className="flex size-14 items-center justify-center rounded-full bg-primary-dark text-white shadow-[0_8px_24px_rgba(15,23,42,0.28)] transition-transform hover:scale-105"
      >
        {open ? <X className="size-6" aria-hidden /> : <Bot className="size-6" aria-hidden />}
      </button>
    </div>
  )
}
