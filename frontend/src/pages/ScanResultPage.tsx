
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Link, useParams } from 'react-router-dom'
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  Check,
  ChevronLeft,
  ChevronRight,
  ListChecks,
  Loader2,
  RefreshCw,
  XCircle,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { apiRequest, apiRequestWithMeta, ApiError } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useExchangeRates } from '@/shared/hooks/useExchangeRates'
import { CurrencySelect } from '@/shared/components/CurrencySelect'
import { formatConvertedAmount, type ExchangeRates } from '@/shared/lib/currency'
import { assessDish, hasRisk, type DietProfile } from '@/features/menu-scan/dietary'
import { isProfileActive, rankDishes } from '@/features/menu-scan/ranking'
import type {
  MenuItemResult,
  MenuDetail,
  MenuSavedState,
  PaginationMeta,
  ScanDetail,
  ScanError,
  ScanResult,
} from '@/features/menu-scan/types'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { SectionCard } from '@/shared/components/SectionCard'
import { IconBadge } from '@/shared/components/IconBadge'
import { EmptyState } from '@/shared/components/EmptyState'
import { Spinner } from '@/shared/components/Spinner'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'

const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

function resolveUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`
}

const POLL_INTERVAL_MS = 1500
const MAX_POLL_MS = 180_000 // 3 min cap; the pipeline finishes well under this.
const SCAN_RESULT_ITEMS_PAGE_SIZE = 6

const LANGUAGE_MAP: Record<string, string> = {
  vi: '🇻🇳 Tiếng Việt',
  en: '🇺🇸 English',
  zh: '🇨🇳 中文',
  ja: '🇯🇵 日本語',
  ko: '🇰🇷 한국어',
  fr: '🇫🇷 Français',
  th: '🇹🇭 ภาษาไทย',
}

export function ScanResultPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const { accessToken, user } = useAuth()
  const { t } = useTranslation()
  useDocumentTitle(`${t('scanResult.title')} | MenuScan`)

  const [detail, setDetail] = useState<ScanDetail | null>(null)
  const [result, setResult] = useState<ScanResult | null>(null)
  const [resultMeta, setResultMeta] = useState<PaginationMeta | null>(null)
  const [error, setError] = useState<string | null>(null)
  const startedAt = useRef(0)

  // Clear stale results the moment the route points at a different scan, using
  // the documented React pattern for resetting state on a prop change (compare a
  // stored value during render). This keeps the polling effect free of
  // synchronous setState calls.
  const [shownScanId, setShownScanId] = useState(scanId)
  if (shownScanId !== scanId) {
    setShownScanId(scanId)
    setResult(null)
    setResultMeta(null)
    setError(null)
  }

  const fetchResultPage = useCallback(
    async (page: number) => {
      if (!scanId) return
      return apiRequestWithMeta<ScanResult, PaginationMeta>(
        `/api/v1/scans/${scanId}/result?page=${page}&page_size=${SCAN_RESULT_ITEMS_PAGE_SIZE}`,
        { method: 'GET', token: accessToken ?? undefined },
      )
    },
    [accessToken, scanId],
  )

  const loadResultPage = useCallback(
    async (page: number) => {
      const response = await fetchResultPage(page)
      if (!response) return
      setResult(response.data)
      setResultMeta(response.meta)
    },
    [fetchResultPage],
  )

  useEffect(() => {
    if (!scanId) return
    startedAt.current = Date.now()
    let cancelled = false
    let timer = 0

    const poll = async () => {
      try {
        const current = await apiRequest<ScanDetail>(
          `/api/v1/scans/${scanId}`,
          { method: 'GET', token: accessToken ?? undefined },
        )
        if (cancelled) return
        setDetail(current)

        if (current.status === 'COMPLETED') {
          try {
            const response = await fetchResultPage(1)
            if (!cancelled && response) {
              setResult(response.data)
              setResultMeta(response.meta)
            }
          } catch (err) {
            if (!cancelled) {
              setError(
                err instanceof ApiError
                  ? err.message
                  : t('scanResult.errors.resultLoadFailed'),
              )
            }
          }
          return
        }

        if (current.status === 'FAILED') {
          if (!cancelled) {
            const err = current.error
            const msg =
              err == null
                ? t('scanResult.errors.scanFailed')
                : typeof err === 'string'
                  ? err
                  : (err as ScanError).message || t('scanResult.errors.scanFailed')
            setError(msg)
          }
          return
        }

        if (Date.now() - startedAt.current < MAX_POLL_MS) {
          timer = window.setTimeout(poll, POLL_INTERVAL_MS)
        } else {
          setError(t('scanResult.errors.tookTooLong'))
        }
      } catch (err) {
        if (cancelled) return
        setError(
          err instanceof ApiError ? err.message : t('scanResult.errors.statusFailed'),
        )
      }
    }

    timer = window.setTimeout(poll, 0)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [scanId, accessToken, fetchResultPage, t])

  const status = detail?.status
  const handleSavedChange = (isSaved: boolean) => {
    setResult((current) =>
      current?.menu
        ? { ...current, menu: { ...current.menu, is_saved: isSaved } }
        : current,
    )
  }
  const handleConfirmed = (menu: MenuDetail) => {
    setResult((current) =>
      current?.menu
        ? {
            ...current,
            menu: {
              ...current.menu,
              status: menu.status,
              is_saved: menu.is_saved,
              title: menu.title,
              default_currency: menu.default_currency,
              items: current.menu.items,
            },
          }
        : current,
    )
  }

  return (
    <PageTransition>
      <div className="mx-auto w-full max-w-[900px] px-[30px] py-[40px] sm:px-[50px]">
        <Link
          to={user ? '/app' : '/'}
          className="mb-6 flex w-fit items-center gap-2 text-[14px] text-ink-variant transition-colors hover:text-primary"
        >
          <ArrowLeft className="size-4" aria-hidden />
          {user ? t('common.backToDashboard') : t('common.backToHome')}
        </Link>

        {error && (
          <div
            role="alert"
            className="flex flex-col gap-4 rounded-2xl border border-destructive/30 bg-destructive/5 px-5 py-4"
          >
            <div className="flex items-start gap-3 text-[14px] text-destructive">
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>{error}</span>
            </div>
            <Button
              asChild
              variant="outline"
              className="w-fit border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
            >
              <Link to="/app/scan">
                <RefreshCw className="size-4" aria-hidden />
                {t('scanResult.retryScan')}
              </Link>
            </Button>
          </div>
        )}

        {!error && status !== 'COMPLETED' && <ProcessingView detail={detail} />}

        {status === 'COMPLETED' && result && (
          <ResultView
            result={result}
            itemsMeta={resultMeta}
            accessToken={accessToken}
            onSavedChange={handleSavedChange}
            onConfirmed={handleConfirmed}
            onItemsPageChange={loadResultPage}
          />
        )}
      </div>
    </PageTransition>
  )
}

function ProcessingView({ detail }: { detail: ScanDetail | null }) {
  const { t } = useTranslation()
  const progress = detail?.progress ?? 0
  const fallbackStage = t('scanResult.processing.default')
  const stageLabel = detail?.stage
    ? t(`scanResult.stages.${detail.stage}`, { defaultValue: fallbackStage })
    : fallbackStage
  return (
    <SectionCard>
      <div className="flex flex-col items-center gap-6 px-4 py-8 text-center">
        <Spinner label={t('scanResult.processing.title')} className="text-primary" />
        <div className="flex flex-col gap-2">
          <h1 className="text-[24px] font-bold leading-[30px] text-ink">
            {t('scanResult.processing.title')}
          </h1>
          <p className="text-[14px] text-ink-variant">{stageLabel}</p>
          <div className="flex items-center justify-center gap-1.5" aria-hidden>
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="size-2 rounded-full bg-primary"
                animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
                transition={{ duration: 1, repeat: Infinity, delay: i * 0.15, ease: 'easeInOut' }}
              />
            ))}
          </div>
        </div>
        <div className="flex w-full max-w-md flex-col gap-2">
          <div className="h-2 w-full overflow-hidden rounded-full bg-panel">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500 ease-[var(--ease-out-quint)]"
              style={{ width: `${Math.max(5, progress)}%` }}
            />
          </div>
          <span className="text-right text-[13px] text-ink-variant">{progress}%</span>
        </div>
      </div>
    </SectionCard>
  )
}

function ResultView({
  result,
  itemsMeta,
  accessToken,
  onSavedChange,
  onConfirmed,
  onItemsPageChange,
}: {
  result: ScanResult
  itemsMeta: PaginationMeta | null
  accessToken: string | null
  onSavedChange: (isSaved: boolean) => void
  onConfirmed: (menu: MenuDetail) => void
  onItemsPageChange: (page: number) => Promise<void>
}) {
  const { t } = useTranslation()
  const items = result.menu?.items ?? []
  const toast = useToast()
  const source = result.scan.source
  const baseCurrency = result.menu?.default_currency ?? 'VND'
  // Null until the diner picks one: the menu is shown in the currency it is priced
  // in, and rates are only fetched if they ask to see something else.
  const [pickedCurrency, setPickedCurrency] = useState<string | null>(null)
  const displayCurrency = pickedCurrency ?? baseCurrency
  const { rates } = useExchangeRates(baseCurrency, displayCurrency !== baseCurrency)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [itemsLoading, setItemsLoading] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [confirmError, setConfirmError] = useState<string | null>(null)
  const totalItems = itemsMeta?.total ?? items.length

  const handleItemsPageChange = async (page: number) => {
    if (itemsLoading) return
    setItemsLoading(true)
    try {
      await onItemsPageChange(page)
    } catch (err) {
      const description = err instanceof ApiError ? err.message : undefined
      toast.show({
        variant: 'error',
        title: t('scanResult.errors.resultLoadFailed'),
        description,
      })
    } finally {
      setItemsLoading(false)
    }
  }

  const handleToggleSaved = async () => {
    if (!result.menu || saving) return
    const nextSaved = !result.menu.is_saved
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await apiRequest<MenuSavedState>(
        `/api/v1/menus/${result.menu.id}`,
        {
          method: 'PATCH',
          token: accessToken ?? undefined,
          body: JSON.stringify({ is_saved: nextSaved }),
        },
      )
      onSavedChange(updated.is_saved)
      toast.show({
        variant: 'success',
        title: nextSaved ? t('scanResult.toast.saved') : t('scanResult.toast.unsaved'),
      })
    } catch (err) {
      setSaveError(
        err instanceof ApiError
          ? err.message
          : t('scanResult.errors.saveFailed'),
      )
    } finally {
      setSaving(false)
    }
  }

  const handleConfirm = async () => {
    if (!result.menu || confirming) return
    setConfirming(true)
    setConfirmError(null)
    try {
      const confirmed = await apiRequest<MenuDetail>(
        `/api/v1/menus/${result.menu.id}/confirm`,
        {
          method: 'POST',
          token: accessToken ?? undefined,
        },
      )
      onConfirmed(confirmed)
      toast.show({ variant: 'success', title: t('scanResult.toast.confirmed') })
    } catch (err) {
      setConfirmError(
        err instanceof ApiError
          ? err.message
          : t('scanResult.errors.confirmFailed'),
      )
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <IconBadge icon={Check} size="sm" solid />
          <div className="flex flex-col">
            <h1 className="text-[28px] font-bold leading-[34px] text-ink">
              {result.menu?.title || t('scanResult.title')}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <span className="text-[14px] text-ink-variant">
                {t('scanResult.dishCount', { count: totalItems })} · {source.file_name}
              </span>
              <span className="hidden text-[14px] text-ink-variant sm:inline">•</span>
              {result.scan.detected_language && (
                <Badge variant="secondary">
                  {t('scanResult.detected')} {LANGUAGE_MAP[result.scan.detected_language] || result.scan.detected_language.toUpperCase()}
                </Badge>
              )}
              <Badge variant="primary">
                {t('scanResult.translatedTo')} {LANGUAGE_MAP[result.scan.target_language] || result.scan.target_language.toUpperCase()}
              </Badge>
            </div>
          </div>
        </div>
        {result.menu && (
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <Button asChild>
              <Link to={`/app/menus/${result.menu.id}`}>
                <ListChecks className="size-4" aria-hidden />
                {t('scanResult.chooseAndSplit')}
              </Link>
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleConfirm}
              disabled={confirming}
            >
              {confirming ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Check className="size-4" aria-hidden />
              )}
              {result.menu.status === 'CONFIRMED' ? t('scanResult.confirmed') : t('scanResult.confirmMenu')}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleToggleSaved}
              disabled={saving}
              aria-pressed={result.menu.is_saved}
            >
              {saving ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : result.menu.is_saved ? (
                <BookmarkCheck className="size-4" aria-hidden />
              ) : (
                <Bookmark className="size-4" aria-hidden />
              )}
              {result.menu.is_saved ? t('scanResult.saved') : t('scanResult.saveMenu')}
            </Button>
            {saveError && (
              <span role="alert" className="text-[13px] text-destructive">
                {saveError}
              </span>
            )}
            {confirmError && (
              <span role="alert" className="text-[13px] text-destructive">
                {confirmError}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-[30px] lg:grid-cols-[300px_minmax(0,1fr)]">
        <SourcePreview source={source} accessToken={accessToken} />
        <ItemsList
          items={items}
          baseCurrency={baseCurrency}
          displayCurrency={displayCurrency}
          rates={rates}
          onCurrencyChange={setPickedCurrency}
          itemsMeta={itemsMeta}
          itemsLoading={itemsLoading}
          onPageChange={(page) => void handleItemsPageChange(page)}
        />
      </div>
    </div>
  )
}

/** Fetch the source bytes and render an object URL. Auth is optional because
 * guest scans can read their source by scan id. */
function SourcePreview({
  source,
  accessToken,
}: {
  source: ScanResult['scan']['source']
  accessToken: string | null
}) {
  const { t } = useTranslation()
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const isImage = source.mime_type.startsWith('image/')

  useEffect(() => {
    if (!isImage) return
    let url: string | null = null
    let active = true
    const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
    fetch(resolveUrl(source.preview_url), { headers, credentials: 'include' })
      .then((res) => (res.ok ? res.blob() : Promise.reject(new Error(`${res.status}`))))
      .then((blob) => {
        if (!active) return
        url = URL.createObjectURL(blob)
        setObjectUrl(url)
      })
      .catch(() => active && setObjectUrl(null))
    return () => {
      active = false
      if (url) URL.revokeObjectURL(url)
    }
  }, [source.preview_url, accessToken, isImage])

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[14px] font-medium uppercase tracking-[0.7px] text-ink-variant">
        {t('scanResult.sourceFile')}
      </p>
      <div className="overflow-hidden rounded-2xl border border-border bg-panel shadow-2">
        {isImage ? (
          objectUrl ? (
            <img
              src={objectUrl}
              alt={source.file_name}
              className="h-auto w-full object-contain"
            />
          ) : (
            <div className="flex aspect-square items-center justify-center">
              <Loader2 className="size-6 animate-spin text-ink-variant" aria-hidden />
            </div>
          )
        ) : (
          <div className="flex items-center gap-3 p-4">
            <AlertCircle className="size-5 text-primary" aria-hidden />
            <span className="text-[14px] text-ink-variant">
              {source.file_name} (PDF)
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * What the scan actually read off the menu — names, prices, descriptions,
 * allergen warnings. Nothing else.
 *
 * This card used to render taste meters, ingredient tags and a "100/100
 * recommended" verdict. None of that data exists yet at this point in the flow:
 * the tags come from the enrichment pass, which runs on the menu screen. So the
 * card was mostly blank, and the verdict was scored against empty tags — which is
 * how every single dish ended up "recommended". Advice belongs on the next screen,
 * where it has something to stand on.
 */
const ExtractedMenuItemCard = memo(function ExtractedMenuItemCard({
  item,
  dietProfile,
  baseCurrency,
  displayCurrency,
  rates,
}: {
  item: MenuItemResult
  dietProfile: DietProfile
  baseCurrency: string
  displayCurrency: string
  rates: ExchangeRates | null
}) {
  const { t } = useTranslation()
  const displayPrice = useMemo(() => {
    if (!item.price) return '—'
    return formatConvertedAmount(
      Number(item.price),
      item.currency ?? baseCurrency,
      displayCurrency,
      rates,
    )
  }, [baseCurrency, displayCurrency, item.currency, item.price, rates])

  const description = item.translated_description || item.original_description

  // Two different things, deliberately styled differently.
  //
  // A WARNING is personal: this dish contains something YOU told us to avoid. It
  // is red, and it only fires on a real match. Dumping every allergen a dish
  // contains under a ⚠ told a diner with no declared allergies that half the menu
  // was dangerous — and a warning that cries wolf is worse than none, because they
  // learn to scroll past the one that finally matters.
  //
  // The allergen LIST is just information: what's in the dish. A guest who has
  // declared nothing still needs it, so it stays — neutral, not alarming, and in
  // their own language rather than raw codes like "gluten, soy".
  const risk = useMemo(() => assessDish(item, dietProfile), [dietProfile, item])
  const risky = hasRisk(risk)
  const allergenList = useMemo(
    () => (item.allergens ?? []).map((code) => t(`diet.allergens.${code}`)),
    [item.allergens, t],
  )

  return (
    <article className="flex h-full flex-col gap-3 rounded-2xl border border-border bg-surface p-4 shadow-2 transition-all duration-200 ease-[var(--ease-out-quint)] hover:-translate-y-1 hover:shadow-3">
      <div className="flex min-h-7 items-start justify-between gap-3">
        {item.category ? (
          <span className="max-w-[65%] truncate rounded-lg bg-panel px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.5px] text-ink-variant">
            {item.category}
          </span>
        ) : (
          <span aria-hidden />
        )}
        <span className="shrink-0 text-[15px] font-bold text-primary-dark">
          {displayPrice}
        </span>
      </div>

      {/* The translated name leads. The diner asked for this menu in their language;
          showing them the German name in bold and burying the Vietnamese one under
          it hands them back exactly the problem they opened the app to solve. The
          original stays visible underneath — they still have to point at something
          on the paper menu to order it. */}
      <div className="flex flex-col gap-1">
        <h3 className="break-words text-[16px] font-bold leading-snug text-ink">
          {item.translated_name || item.original_name}
        </h3>
        {item.translated_name && item.translated_name !== item.original_name && (
          <p className="break-words text-[13px] font-medium text-ink-variant/70">
            {item.original_name}
          </p>
        )}
      </div>

      {description && (
        <div className="border-t border-border pt-3">
          <p className="line-clamp-4 text-[13px] leading-relaxed text-ink-variant">
            {description}
          </p>
        </div>
      )}

      {(risky || allergenList.length > 0) && (
        <div className="mt-auto flex flex-col gap-1.5">
          {risky && (
            <p className="flex gap-1.5 rounded-lg border border-destructive/30 bg-destructive/5 px-2 py-1.5 text-[11px] font-bold leading-relaxed text-destructive">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              <span>
                {risk.allergens.length > 0
                  ? t('billItem.allergyMatch', {
                      list: risk.allergens
                        .map((code) => t(`diet.allergens.${code}`))
                        .join(', '),
                    })
                  : t('billItem.dietMatch', {
                      list: risk.dietFlags
                        .map((code) => t(`diet.preferences.${code}`))
                        .join(', '),
                    })}
              </span>
            </p>
          )}
          {allergenList.length > 0 && (
            <p className="text-[11px] leading-relaxed text-ink-variant">
              {t('billItem.contains', { list: allergenList.join(', ') })}
            </p>
          )}
        </div>
      )}
    </article>
  )
})

function ItemsList({
  items,
  baseCurrency,
  displayCurrency,
  rates,
  onCurrencyChange,
  itemsMeta,
  itemsLoading,
  onPageChange,
}: {
  items: MenuItemResult[]
  baseCurrency: string
  displayCurrency: string
  rates: ExchangeRates | null
  onCurrencyChange: (currency: string) => void
  itemsMeta: PaginationMeta | null
  itemsLoading: boolean
  onPageChange: (page: number) => void
}) {
  const { t } = useTranslation()
  const { user } = useAuth()
  // Personalize the scan result: rank best-fit dishes up (reusing assessDish)
  // and flag risky ones. With no profile, keep the extracted order.
  const dietProfile = useMemo<DietProfile>(
    () => ({
      allergies: user?.allergies ?? [],
      dietary_preferences: user?.dietary_preferences ?? [],
    }),
    [user?.allergies, user?.dietary_preferences],
  )
  const profileActive = isProfileActive(dietProfile)
  const rankedItems = useMemo(
    () => (profileActive ? rankDishes(items, dietProfile) : items),
    [profileActive, items, dietProfile],
  )
  const showPagination = itemsMeta !== null && itemsMeta.total_pages > 1
  const pageStart =
    itemsMeta && items.length > 0
      ? (itemsMeta.page - 1) * itemsMeta.page_size + 1
      : 0
  const pageEnd = itemsMeta
    ? Math.min(itemsMeta.page * itemsMeta.page_size, itemsMeta.total)
    : items.length
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[14px] font-medium uppercase tracking-[0.7px] text-ink-variant">
          {t('scanResult.extractedItems')}
        </p>
        {items.length > 0 && (
          <CurrencySelect value={displayCurrency} onChange={onCurrencyChange} />
        )}
      </div>
      {items.length === 0 ? (
        <SectionCard>
          <EmptyState
            icon={XCircle}
            title={t('scanResult.noItems.title')}
            description={t('scanResult.noItems.body')}
            action={
              <Button asChild>
                <Link to="/app/scan">{t('scanResult.scanAnother')}</Link>
              </Button>
            }
          />
        </SectionCard>
      ) : (
        <>
          <Reveal className="grid grid-cols-1 items-stretch gap-4 sm:grid-cols-2 2xl:grid-cols-3">
            {rankedItems.map((item) => (
              <ExtractedMenuItemCard
                key={item.id}
                item={item}
                dietProfile={dietProfile}
                baseCurrency={baseCurrency}
                displayCurrency={displayCurrency}
                rates={rates}
              />
            ))}
          </Reveal>
          {showPagination && itemsMeta && (
            <div className="flex flex-col items-center justify-between gap-3 rounded-2xl border border-border bg-surface px-3 py-2 shadow-1 sm:flex-row">
              <p className="text-[13px] text-ink-variant" aria-live="polite">
                {t('scanResult.pageStatus', {
                  from: pageStart,
                  to: pageEnd,
                  total: itemsMeta.total,
                })}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="icon-sm"
                  onClick={() => onPageChange(itemsMeta.page - 1)}
                  disabled={itemsLoading || itemsMeta.page <= 1}
                  aria-label={t('scanResult.prevPage')}
                >
                  <ChevronLeft className="size-4" aria-hidden />
                </Button>
                <span className="min-w-[72px] text-center text-[13px] font-bold text-ink">
                  {itemsMeta.page} / {itemsMeta.total_pages}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="icon-sm"
                  onClick={() => onPageChange(itemsMeta.page + 1)}
                  disabled={itemsLoading || itemsMeta.page >= itemsMeta.total_pages}
                  aria-label={t('scanResult.nextPage')}
                >
                  {itemsLoading ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <ChevronRight className="size-4" aria-hidden />
                  )}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
