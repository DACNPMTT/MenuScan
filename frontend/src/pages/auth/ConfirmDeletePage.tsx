<<<<<<< HEAD
import { useEffect, useState } from 'react'
=======
import { useState } from 'react'
>>>>>>> origin/main
import { useSearchParams } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { motion } from 'motion/react'
import { Button } from '@/shared/components/ui/button'
import { CryingMascot } from '@/shared/components/mascot/CryingMascot'

export function ConfirmDeletePage() {
  const { t } = useTranslation()
  useDocumentTitle(t('deleteAccount.confirmTitle') + ' | MenuScan')
  const { confirmDeleteAccount } = useAuth()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    if (!token) {
      let active = true
      Promise.resolve().then(() => {
        if (active) {
          setStatus('error')
          setErrorMessage(t('deleteAccount.errors.missingToken'))
        }
      })
      return () => { active = false }
    }
  }, [token, t])

  const handleConfirm = () => {
    if (!token) return
    setStatus('loading')
    confirmDeleteAccount(token)
      .then(() => {
        setStatus('success')
      })
      .catch((error) => {
        setStatus('error')
        setErrorMessage(
          error instanceof Error ? error.message : t('deleteAccount.errors.unknown')
        )
      })
  }

  return (
    <PageTransition>
      <div className="flex min-h-[100dvh] flex-col items-center justify-center bg-app-bg px-6 py-12 text-center">
        {status === 'success' ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="flex w-full max-w-[600px] flex-col items-center justify-center"
          >
            <div className="w-32 sm:w-40 md:w-48 aspect-[4/5] mx-auto">
              <CryingMascot size={undefined} className="w-full h-full" />
            </div>
            
            <motion.h1 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.5, ease: 'easeOut' }}
              className="mt-6 sm:mt-8 text-[28px] sm:text-[36px] md:text-[40px] font-extrabold text-ink tracking-tight"
            >
              {t('deleteAccount.deleted')}
            </motion.h1>
            
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="mt-2 sm:mt-3 flex flex-col items-center gap-1.5 px-4"
            >
              <p className="text-[15px] sm:text-[17px] font-medium text-ink-variant leading-snug">
                {t('deleteAccount.deletedDesc')}
              </p>
              <p className="text-[16px] sm:text-[18px] md:text-[20px] font-bold text-primary">
                {t('deleteAccount.seeYouNextMeal')}
              </p>
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7, duration: 0.5, ease: 'easeOut' }}
              className="mt-10 sm:mt-12 w-full max-w-[260px] sm:max-w-[300px]"
            >
              <Button
                size="lg"
                className="w-full rounded-2xl h-14 text-[16px]"
                onClick={() => { window.location.href = '/' }}
              >
                {t('deleteAccount.backToHome')}
              </Button>
            </motion.div>
          </motion.div>
        ) : (
          <div className="w-full max-w-[440px] rounded-2xl border border-border bg-canvas p-8 text-center shadow-2">
            {status === 'idle' && (
              <>
                <AlertCircle className="mx-auto size-12 text-destructive" />
                <h1 className="mt-4 text-[20px] font-bold text-ink">
                  {t('deleteAccount.confirmTitle')}
                </h1>
                <p className="mt-2 mb-6 text-[14px] text-ink-variant">
                  {t('deleteAccount.warning')}
                </p>
                <Button
                  size="lg"
                  variant="destructive"
                  className="w-full h-12 text-[15px]"
                  onClick={handleConfirm}
                >
                  {t('deleteAccount.confirmDeleteButton')}
                </Button>
              </>
            )}

            {status === 'loading' && (
              <>
                <Loader2 className="mx-auto size-12 animate-spin text-primary" />
                <h1 className="mt-4 text-[20px] font-bold text-ink">
                  {t('deleteAccount.processing')}
                </h1>
                <p className="mt-2 text-[14px] text-ink-variant">
                  {t('deleteAccount.processingDesc')}
                </p>
              </>
            )}

            {status === 'error' && (
              <>
                <AlertCircle className="mx-auto size-12 text-destructive" />
                <h1 className="mt-4 text-[20px] font-bold text-ink">
                  {t('deleteAccount.errors.title')}
                </h1>
                <p className="mt-2 text-[14px] text-destructive">{errorMessage}</p>
              </>
            )}
          </div>
        )}
      </div>
    </PageTransition>
  )
}
