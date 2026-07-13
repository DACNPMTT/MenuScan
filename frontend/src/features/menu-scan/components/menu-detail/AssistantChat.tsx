import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, PointerEvent as ReactPointerEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Bot, Loader2, Plus, Send, X } from 'lucide-react'
import { apiRequest, ApiError } from '@/shared/lib/api'

/** Seconds the server told us to wait, from the 429's `details.retry_after`. */
function retryAfterSeconds(details: unknown): number {
  if (details && typeof details === 'object' && 'retry_after' in details) {
    const value = Number((details as { retry_after: unknown }).retry_after)
    if (Number.isFinite(value) && value > 0) return Math.ceil(value)
  }
  return 5
}

/** `crypto.randomUUID` is undefined outside a secure context — a phone opening the
 *  app over plain http on a LAN IP would throw inside send(). */
function messageId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

/** Lightweight markdown renderer for chat bubbles.
 *  Supports: **bold**, - bullet lists, blank-line paragraphs, and ⚠️ lines.
 *  No external dependency required. */
const ChatMarkdown = memo(function ChatMarkdown({ text }: { text: string }) {
  const paragraphs = useMemo(() => text.split(/\n{2,}/), [text])
  return (
    <div className="chat-md">
      {paragraphs.map((block, bi) => {
        const lines = block.split('\n').filter((line) => line.trim())
        const bullets = lines.filter((l) => /^\s*[-•]\s/.test(l))

        // All lines are bullets → render as <ul>
        if (bullets.length === lines.length && bullets.length > 0) {
          return (
            <ul key={bi} className="my-1 ml-3.5 list-disc space-y-0.5">
              {bullets.map((b, li) => (
                <li key={li}>
                  <BoldText text={b.replace(/^\s*[-•]\s*/, '')} />
                </li>
              ))}
            </ul>
          )
        }

        // Mixed or plain text → render as <p>
        return (
          <p key={bi} className="my-1">
            {lines.map((line, li) => (
              <span key={li}>
                {li > 0 && <br />}
                <BoldText text={line} />
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
})

/** Render **bold** spans inside a line of text. */
function BoldText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith('**') && part.endsWith('**') ? (
          <strong key={i} className="font-semibold">
            {part.slice(2, -2)}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  )
}

interface ChatMsg {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** An error bubble we rendered locally — NOT something the model said. */
  isError?: boolean
}

export interface SelectedDish {
  id: string
  name: string
}

interface AssistantChatProps {
  menuId: string
  /** Dishes the diner has added (quantity > 0), for quick-ask chips + picker. */
  selectedDishes?: SelectedDish[]
  /** Id of the most recently added dish — suggested for a quick question. */
  lastSelectedId?: string | null
}

/** Floating assistant (Messenger-style): a draggable bot bubble parked in a
 * corner. Tapping it opens the chat panel docked at the bottom-right (above the
 * bubble, so the bubble never covers it); tapping again closes. Grounded on the
 * scanned menu; history is ephemeral (local state only). */
export const AssistantChat = memo(function AssistantChat({
  menuId,
  selectedDishes = [],
  lastSelectedId,
}: AssistantChatProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  // Seconds left on the server's cooldown. Send stays disabled until it hits 0,
  // instead of letting the diner hammer the button and collect more 429s.
  const [cooldown, setCooldown] = useState(0)
  // Dishes the question is focused on (by id). Empty = ask about the whole menu.
  const [focusIds, setFocusIds] = useState<string[]>([])
  const [pickerOpen, setPickerOpen] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, loading])

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setTimeout(() => setCooldown((value) => value - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [cooldown])

  // --- Draggable bubble: parked at `pos` when closed; snaps to the bottom-right
  // corner while open so it stays consistent and never covers the chat. ---
  const containerRef = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null)
  const drag = useRef<{
    startX: number
    startY: number
    dx: number
    dy: number
    moved: boolean
  } | null>(null)
  const FAB = 56

  const onPointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    drag.current = {
      startX: event.clientX,
      startY: event.clientY,
      dx: event.clientX - rect.left,
      dy: event.clientY - rect.top,
      moved: false,
    }
    event.currentTarget.setPointerCapture(event.pointerId)
  }
  const onPointerMove = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const d = drag.current
    if (!d || open) return // no dragging while the panel is open
    if (!d.moved && Math.hypot(event.clientX - d.startX, event.clientY - d.startY) < 5) {
      return
    }
    d.moved = true
    const left = Math.min(Math.max(event.clientX - d.dx, 8), window.innerWidth - FAB - 8)
    const top = Math.min(Math.max(event.clientY - d.dy, 8), window.innerHeight - FAB - 8)
    setPos({ left, top })
  }
  const onPointerUp = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const d = drag.current
    drag.current = null
    event.currentTarget.releasePointerCapture?.(event.pointerId)
    // A tap (no drag) toggles the panel.
    if (d && !d.moved) setOpen((value) => !value)
  }

  // Resolve focus against the current selection so removed dishes drop out.
  const focusDishes = focusIds
    .map((id) => selectedDishes.find((dish) => dish.id === id))
    .filter((dish): dish is SelectedDish => dish !== undefined)

  // Match on id, not on display name. Two dishes can share a name ("Chop Suey"
  // with a chicken and a beef variant) and the name lookup focused whichever came
  // first — sometimes the wrong dish.
  const lastSelected = lastSelectedId
    ? selectedDishes.find((dish) => dish.id === lastSelectedId)
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

  const send = useCallback(
    async (event: FormEvent) => {
      event.preventDefault()
      const question = input.trim()
      if (!question || loading || cooldown > 0) return

      // Error bubbles are OUR text, not the model's. Feeding them back as history
      // meant Gemini received "You're asking a bit fast, please wait" as its own
      // previous answer and had to reason around it.
      const history = messages
        .filter((message) => !message.isError)
        .slice(-6)
        .map(({ role, content }) => ({ role, content }))
      const focus_dishes = focusDishes.map((dish) => dish.name)

      setMessages((prev) => [
        ...prev,
        { id: messageId(), role: 'user', content: question },
      ])
      setInput('')
      setLoading(true)

      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      try {
        const res = await apiRequest<{ answer: string }>('/api/v1/advisor/chat', {
          method: 'POST',
          body: JSON.stringify({ menu_id: menuId, question, history, focus_dishes }),
          signal: controller.signal,
        })
        setMessages((prev) => [
          ...prev,
          { id: messageId(), role: 'assistant', content: res.answer },
        ])
      } catch (error) {
        if (controller.signal.aborted) return
        const rateLimited = error instanceof ApiError && error.status === 429
        if (rateLimited) {
          setCooldown(retryAfterSeconds(error.details))
        }
        setMessages((prev) => [
          ...prev,
          {
            id: messageId(),
            role: 'assistant',
            content: rateLimited ? t('chat.rateLimited') : t('chat.error'),
            isError: true,
          },
        ])
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    },
    [cooldown, focusDishes, input, loading, menuId, messages, t],
  )

  return (
    <div
      ref={containerRef}
      className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3"
      // While open, ignore the parked position so the bubble + panel snap to the
      // bottom-right corner. When closed, sit wherever the bubble was dragged.
      style={
        !open && pos
          ? { left: pos.left, top: pos.top, right: 'auto', bottom: 'auto' }
          : undefined
      }
    >
      {open && (
        <div className="flex h-[min(78vh,600px)] w-[min(92vw,440px)] flex-col overflow-hidden rounded-[16px] border border-hairline bg-canvas shadow-[0_16px_50px_rgba(15,23,42,0.24)]">
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
                  {message.role === 'assistant' ? (
                    <ChatMarkdown text={message.content} />
                  ) : (
                    message.content
                  )}
                </div>
              ))
            )}
            {loading && (
              <div className="self-start rounded-[10px] border border-hairline bg-surface-muted px-3 py-2 text-ink-variant">
                <Loader2 className="size-4 animate-spin" aria-hidden />
              </div>
            )}
            <div ref={bottomRef} />
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
              disabled={loading || cooldown > 0 || !input.trim()}
              aria-label={t('chat.send')}
              className="flex size-10 shrink-0 items-center justify-center rounded-[8px] bg-primary-dark text-[12px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {cooldown > 0 ? cooldown : <Send className="size-4" aria-hidden />}
            </button>
          </form>

          <p className="border-t border-hairline px-4 py-2 text-[11px] text-ink-variant">
            {t('chat.disclaimer')}
          </p>
        </div>
      )}

      <button
        type="button"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        aria-label={t('chat.title')}
        aria-expanded={open}
        className="flex size-14 touch-none cursor-grab items-center justify-center rounded-full bg-primary-dark text-white shadow-[0_8px_24px_rgba(15,23,42,0.28)] transition-transform hover:scale-105 active:cursor-grabbing"
      >
        <Bot className="size-6" aria-hidden />
      </button>
    </div>
  )
})
