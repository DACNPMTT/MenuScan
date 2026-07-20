import { useState } from 'react'
import { Users } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useToast } from '@/app/providers/ToastProvider'
import { cn } from '@/shared/lib/cn'
import { createDiningSessionFromRestaurant } from '../api'

interface InviteFriendsHereProps {
  restaurantSourceId: number
  className?: string
}

/**
 * "Invite friends here" — group-bridge button used on the card and detail page.
 *
 * Creates a dining session tagged with the restaurant, then navigates the host
 * to the existing `HostDiningSessionPage` so they can share the invite link.
 */
export function InviteFriendsHere({
  restaurantSourceId,
  className,
}: InviteFriendsHereProps) {
  const { t } = useTranslation()
  const toast = useToast()
  const navigate = useNavigate()
  const [pending, setPending] = useState(false)

  const onClick = async () => {
    setPending(true)
    try {
      const result = await createDiningSessionFromRestaurant(restaurantSourceId)
      toast.show({
        variant: 'success',
        title: t('feed.toast.sessionCreated'),
      })
      navigate(`/app/dining/sessions/${result.session.id}`)
    } catch (err) {
      toast.show({
        variant: 'error',
        title: err instanceof Error ? err.message : t('common.retry'),
      })
    } finally {
      setPending(false)
    }
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pending}
      className={cn(
        'flex items-center justify-center gap-2 rounded-2xl border border-primary bg-primary/5 px-4 py-3 text-[14px] font-bold text-primary transition-all hover:bg-primary/10',
        pending && 'cursor-not-allowed opacity-60',
        className,
      )}
    >
      <Users className="size-4" aria-hidden />
      {t('feed.detail.inviteFriends')}
    </button>
  )
}
