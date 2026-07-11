import { useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Bot, Loader2, Plus, Send, X } from 'lucide-react'
import { apiRequest, ApiError } from '@/shared/lib/api'

interface ChatMsg {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export interface SelectedDish {
  id: string
  name: string
}

interface AssistantChatProps {
  menuId: string
  /** Dishes the diner has added (quantity > 0), for quick-ask chips + picker. */
  selectedDishes?: SelectedDish[]
  /** Name of the most recently added dish — suggested for a quick question. */
  lastSelectedName?: string
}

/** Floating assistant: a fixed bot button (always visible while scrolling) that
 * toggles a chat panel. Grounded on the scanned menu; can focus the answer on
 * the dishes the diner selected. History is ephemeral (local state only). */
export function AssistantChat({
  menuId,
  selectedDishes = [],
  lastSelectedName,
}: AssistantChatProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  // Dishes the question is focused on (by id). Empty = ask about the whole menu.
  const [focusIds, setFocusIds] = useState<string[]>([])
  const [pickerOpen, setPickerOpen] = useState(false)

  // Resolve focus against the current selection so removed dishes drop out.
  const focusDishes = focusIds
    .map((id) => selectedDishes.find((dish) => dish.id === id))
    .filter((dish): dish is SelectedDish => dish !== undefined)

  const lastSelected = lastSelectedName
    ? selectedDishes.find((dish) => dish.name === lastSelectedName)
    : undefined
  const suggestion =
    lastSelected && !focusIds.includes(lastSelected.id) ? lastSelected : undefined

  const addFocus = (id: string) => {
    setFocusIds((prev) => (prev.includes(id) ? prev : [...prev, id]))
    setPickerOpen(false)
  }
  const removeFocus = (id: string) =>
    setFocusIds((prev) => prev.filter((value) => value !== id))
  const focusAll = () => {
    setFocusIds(selectedDishes.map((dish) => dish.id))
    setPickerOpen(false)
  }

  const send = async (event: FormEvent) => {
    event.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    const history = messages.slice(-6).map(({ role, content }) => ({ role, content }))
    const focus_dishes = focusDishes.map((dish) => dish.name)
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: question },
    ])
    setInput('')
    setLoading(true)
    try {
      const res = await apiRequest<{ answer: string }>('/api/v1/advisor/chat', {
        method: 'POST',
        body: JSON.stringify({ menu_id: menuId, question, history, focus_dishes }),
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
        <div className="flex max-h-[78vh] w-[min(94vw,460px)] flex-col overflow-hidden rounded-[14px] border border-hairline bg-canvas shadow-[0_12px_40px_rgba(15,23,42,0.18)]">
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

          {/* Focus chips + last-selected suggestion */}
          {(focusDishes.length > 0 || suggestion) && (
            <div className="flex flex-wrap items-center gap-1.5 border-t border-hairline px-4 py-2">
              {focusDishes.map((dish) => (
                <span
                  key={dish.id}
                  className="flex items-center gap-1 rounded-full bg-primary/10 py-1 pl-2.5 pr-1 text-[12px] font-medium text-primary-dark"
                >
                  {dish.name}
                  <button
                    type="button"
                    onClick={() => removeFocus(dish.id)}
                    aria-label={t('chat.removeFocus')}
                    className="flex size-4 items-center justify-center rounded-full hover:bg-primary/20"
                  >
                    <X className="size-3" aria-hidden />
                  </button>
                </span>
              ))}
              {suggestion && (
                <button
                  type="button"
                  onClick={() => addFocus(suggestion.id)}
                  className="rounded-full border border-dashed border-primary-dark/40 px-2.5 py-1 text-[12px] font-medium text-primary-dark transition-colors hover:bg-primary/10"
                >
                  + {t('chat.askAbout', { name: suggestion.name })}
                </button>
              )}
            </div>
          )}

          <form
            onSubmit={send}
            className="relative flex items-center gap-2 border-t border-hairline px-3 py-3"
          >
            {pickerOpen && selectedDishes.length > 0 && (
              <div className="absolute bottom-[calc(100%+4px)] left-3 z-10 max-h-[220px] w-[260px] overflow-y-auto rounded-[10px] border border-hairline bg-canvas py-1 shadow-[0_10px_30px_rgba(15,23,42,0.18)]">
                <button
                  type="button"
                  onClick={focusAll}
                  className="w-full px-3 py-2 text-left text-[13px] font-semibold text-primary-dark hover:bg-surface-muted"
                >
                  {t('chat.allSelected')}
                </button>
                {selectedDishes.map((dish) => (
                  <button
                    key={dish.id}
                    type="button"
                    onClick={() => addFocus(dish.id)}
                    className="w-full truncate px-3 py-2 text-left text-[13px] text-ink hover:bg-surface-muted"
                  >
                    {dish.name}
                  </button>
                ))}
              </div>
            )}
            <button
              type="button"
              onClick={() => setPickerOpen((value) => !value)}
              disabled={selectedDishes.length === 0}
              aria-label={t('chat.pickDish')}
              className="flex size-10 shrink-0 items-center justify-center rounded-[8px] border border-hairline text-primary-dark transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Plus className="size-4" aria-hidden />
            </button>
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
