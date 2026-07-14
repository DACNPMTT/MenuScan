import { Link } from 'react-router-dom'
import { Check, FileJson, PencilLine, ScanText, Sparkles, Star, Upload } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { Button } from '@/shared/components/ui/button'
import { Card } from '@/shared/components/ui/card'
import { Avatar, AvatarFallback } from '@/shared/components/ui/avatar'
import { LanguageSwitcher } from '@/shared/components/LanguageSwitcher'
import { Reveal } from '@/shared/components/motion/Reveal'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { DotGrid } from '@/shared/components/rb/DotGrid'
import { BlurText } from '@/shared/components/rb/BlurText'
import { Magnetic } from '@/shared/components/rb/Magnetic'
import { NonLaMark } from '@/shared/components/mascot/NonLaMark'
import { HeroScene } from '@/shared/components/mascot/HeroScene'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useAuth } from '@/app/providers/AuthProvider'
import { cn } from '@/shared/lib/cn'

const STEP_ICONS = [Upload, ScanText, FileJson, PencilLine]

const EASE = [0.22, 1, 0.36, 1] as const

export function LandingPage() {
  useDocumentTitle('MenuScan')

  return (
    <PageTransition>
      <div className="flex min-h-dvh flex-col bg-white font-duo text-[#3c3c3c]">
        <TopNav />
        <main className="flex-1">
          <Hero />
          <HowItWorks />
          <Partners />
          <Reviews />
          <FinalCTA />
        </main>
        <Footer />
      </div>
    </PageTransition>
  )
}

function TopNav() {
  const { t } = useTranslation()
  const { user } = useAuth()
  return (
    <motion.header
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE }}
      className="sticky top-0 z-30 flex h-[70px] items-center justify-between border-b-2 border-[#e5e5e5] bg-white/90 px-5 backdrop-blur-xl md:px-[75px]"
    >
      <Link to="/" className="flex items-center gap-2.5" aria-label="MenuScan home">
        <span className="flex size-9 items-center justify-center rounded-2xl bg-[#d7ffb8]">
          <NonLaMark size={26} />
        </span>
        <span className="hidden text-[22px] font-black tracking-tight text-[#042c60] min-[420px]:inline">MenuScan</span>
      </Link>
      <nav className="hidden items-center gap-8 md:flex" aria-label="Marketing">
        <a href="#how" className="text-[15px] font-bold text-[#777777] transition-colors hover:text-[#042c60]">
          {t('landing.nav.howItWorks')}
        </a>
        <a href="#partners" className="text-[15px] font-bold text-[#777777] transition-colors hover:text-[#042c60]">
          {t('landing.nav.partners')}
        </a>
        <a href="#reviews" className="text-[15px] font-bold text-[#777777] transition-colors hover:text-[#042c60]">
          {t('landing.nav.reviews')}
        </a>
      </nav>
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <LanguageSwitcher />
        {user ? (
          <Magnetic>
            <Button asChild variant="duo">
              <Link to="/app">{t('landing.nav.goToApp')}</Link>
            </Button>
          </Magnetic>
        ) : (
          <>
            <Button asChild variant="duo-outline">
              <Link to="/auth/login">{t('common.login')}</Link>
            </Button>
            <Magnetic>
              <Button asChild variant="duo">
                <Link to="/auth/register">{t('landing.nav.signup')}</Link>
              </Button>
            </Magnetic>
          </>
        )}
      </div>
    </motion.header>
  )
}

function Hero() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const solves = t('landing.hero.solves', { returnObjects: true }) as string[]
  return (
    <section id="top" className="relative overflow-hidden bg-white px-5 py-16 md:px-[75px] md:py-24">
      {/* Decorative dot grid + soft green blobs — NO gradient */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute inset-0 opacity-50">
          <DotGrid color="rgba(88,204,2,0.14)" />
        </div>
        <div className="absolute left-1/2 top-[-18%] h-[420px] w-[640px] max-w-[120vw] -translate-x-1/2 rounded-full bg-[#58cc02]/8 blur-3xl" />
        <div className="absolute right-[-8%] top-[24%] h-[300px] w-[300px] rounded-full bg-[#a5ed6e]/10 blur-3xl" />
      </div>

      <div className="mx-auto grid max-w-[1152px] grid-cols-1 items-center gap-12 lg:grid-cols-2">
        {/* Text column */}
        <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="mb-6 inline-flex items-center gap-2 rounded-full border-2 border-[#58cc02]/30 bg-white px-4 py-1.5 text-[13px] font-extrabold uppercase tracking-[0.8px] text-[#58cc02] shadow-[0_2px_0_0_#e5e5e5]"
          >
            <Sparkles className="size-4 text-[#58cc02]" aria-hidden />
            {t('landing.hero.badge')}
          </motion.span>

          <BlurText
            as="h1"
            text={t('landing.hero.title')}
            className="max-w-[14ch] text-[44px] font-black leading-[1.05] tracking-[-0.02em] text-[#042c60] md:text-[56px]"
          />

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE, delay: 0.2 }}
            className="mt-6 max-w-[672px] text-[17px] font-medium leading-[26px] text-[#777777] md:text-[18px] md:leading-[28px]"
          >
            {t('landing.hero.subtitle')}
          </motion.p>

          {/* What it solves */}
          <motion.ul
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE, delay: 0.28 }}
            className="mt-6 flex flex-col gap-2.5"
          >
            {solves.map((solve) => (
              <li key={solve} className="flex items-center gap-2.5 text-[15px] font-bold text-[#3c3c3c]">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-[#58cc02]">
                  <Check className="size-3.5 text-white" strokeWidth={3} aria-hidden />
                </span>
                {solve}
              </li>
            ))}
          </motion.ul>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE, delay: 0.36 }}
            className="mt-9 flex flex-col gap-4 sm:flex-row"
          >
            <Magnetic>
              <Button asChild variant="duo" className="h-[52px] px-8 text-[15px]">
                <Link to="/app/scan">{t('landing.hero.startScanning')}</Link>
              </Button>
            </Magnetic>
            {!user && (
              <Button asChild variant="duo-outline" className="h-[52px] px-8 text-[15px]">
                <Link to="/auth/login">{t('common.login')}</Link>
              </Button>
            )}
          </motion.div>
        </div>

        {/* Mascot visual column */}
        <div className="relative flex flex-col items-center justify-center gap-3">
          <div className="w-full max-w-[300px] sm:max-w-[440px]">
            <HeroScene />
          </div>
          <span className="text-[14px] font-bold text-[#58a700]">
            {t('landing.hero.dragHint')}
          </span>
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  const { t } = useTranslation()
  const steps = t('landing.how.steps', { returnObjects: true }) as Array<{
    title: string
    body: string
    tip: string
  }>
  return (
    <section id="how" className="bg-white px-5 py-16 md:px-[75px] md:py-24">
      <div className="mx-auto max-w-[1152px]">
        <Reveal>
          <h2 className="text-center text-[28px] font-black leading-tight tracking-tight text-[#58cc02] sm:text-[34px] md:text-[48px]">
            {t('landing.how.title')}
          </h2>
          <p className="mt-3 text-center text-[17px] font-medium leading-relaxed text-[#777777]">
            {t('landing.how.subtitle')}
          </p>
        </Reveal>
        <div className="relative mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="absolute left-0 right-0 top-7 hidden h-[3px] rounded-full bg-[#58cc02]/20 lg:block" />
          {steps.map((step, index) => {
            const Icon = STEP_ICONS[index] ?? Upload
            return (
              <Reveal
                key={step.title}
                delay={index * 0.08}
                className="relative flex flex-col items-center text-center"
              >
                <div className="flex size-14 items-center justify-center rounded-2xl bg-[#58cc02] text-[22px] font-black text-white shadow-[0_4px_0_0_#58a700]">
                  {index + 1}
                </div>
                <div className="mt-4 flex size-11 items-center justify-center rounded-xl bg-[#d7ffb8]">
                  <Icon className="size-5 text-[#58a700]" aria-hidden />
                </div>
                <h3 className="mt-3 text-[19px] font-extrabold leading-tight text-[#042c60]">
                  {step.title}
                </h3>
                <p className="mt-1 text-[14px] font-medium leading-relaxed text-[#777777]">
                  {step.body}
                </p>
                <span className="mt-2 rounded-full bg-[#fff7e6] px-3 py-1 text-[12px] font-extrabold uppercase tracking-[0.6px] text-[#ff9600]">
                  {step.tip}
                </span>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function Partners() {
  const { t } = useTranslation()
  const items = t('landing.partners.items', { returnObjects: true }) as string[]
  return (
    <section id="partners" className="bg-[#f7f7f7] px-5 py-16 md:px-[75px] md:py-24">
      <div className="mx-auto max-w-[1152px]">
        <Reveal>
          <h2 className="text-center text-[28px] font-black leading-tight tracking-tight text-[#042c60] sm:text-[34px] md:text-[48px]">
            {t('landing.partners.title')}
          </h2>
          <p className="mt-3 text-center text-[17px] font-medium leading-relaxed text-[#777777]">
            {t('landing.partners.subtitle')}
          </p>
        </Reveal>
        <div className="mt-12 grid grid-cols-2 gap-4 md:grid-cols-4">
          {items.map((name, index) => (
            <Reveal key={name} delay={index * 0.05}>
              <div className="flex items-center gap-3 rounded-2xl border-2 border-[#e5e5e5] bg-white px-5 py-4 shadow-[0_4px_0_0_#e5e5e5] transition-all duration-200 hover:-translate-y-0.5 hover:border-[#58cc02]/40">
                <span className="flex size-10 items-center justify-center rounded-xl bg-[#d7ffb8] text-[16px] font-black text-[#58a700]">
                  {name.charAt(0)}
                </span>
                <span className="text-[15px] font-extrabold text-[#3c3c3c]">{name}</span>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex gap-1">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={cn(
            'size-5',
            i < rating ? 'fill-[#ffc800] text-[#ffc800]' : 'text-[#e5e5e5]',
          )}
          aria-hidden
        />
      ))}
    </div>
  )
}

function Reviews() {
  const { t } = useTranslation()
  const items = t('landing.reviews.items', { returnObjects: true }) as Array<{
    quote: string
    name: string
    role: string
    location: string
    rating: number
    initials: string
  }>
  return (
    <section id="reviews" className="bg-white px-5 py-16 md:px-[75px] md:py-24">
      <div className="mx-auto max-w-[1152px]">
        <Reveal>
          <h2 className="text-center text-[28px] font-black leading-tight tracking-tight text-[#58cc02] sm:text-[34px] md:text-[48px]">
            {t('landing.reviews.title')}
          </h2>
          <p className="mt-3 text-center text-[17px] font-medium leading-relaxed text-[#777777]">
            {t('landing.reviews.subtitle')}
          </p>
        </Reveal>
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {items.map((item, index) => (
            <Reveal key={item.name} delay={index * 0.1}>
              <Card className="h-full gap-4 rounded-2xl border-2 border-[#e5e5e5] bg-white p-5 shadow-[0_4px_0_0_#e5e5e5] sm:p-7">
                <Stars rating={item.rating} />
                <p className="text-[16px] font-medium leading-relaxed text-[#3c3c3c]">
                  &ldquo;{item.quote}&rdquo;
                </p>
                <div className="h-px bg-[#e5e5e5]" />
                <div className="flex items-center gap-3">
                  <Avatar>
                    <AvatarFallback className="rounded-full bg-[#d7ffb8] text-[14px] font-black text-[#58a700]">
                      {item.initials}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="text-[14px] font-extrabold text-[#042c60]">{item.name}</div>
                    <div className="text-[14px] font-medium text-[#777777]">
                      {item.role} · {item.location}
                    </div>
                  </div>
                </div>
              </Card>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function FinalCTA() {
  const { t } = useTranslation()
  return (
    <section className="bg-white px-5 py-20 md:px-[75px] md:py-28">
      <Reveal className="mx-auto max-w-[1152px]">
        <div className="overflow-hidden rounded-[24px] bg-[#58cc02] px-5 py-12 text-center shadow-[0_8px_0_0_#58a700] sm:px-6 sm:py-16 md:px-12 md:py-20">
          <NonLaMark size={72} className="mx-auto" />
          <h2 className="mx-auto mt-4 max-w-[24ch] text-[24px] font-black leading-tight tracking-tight text-white sm:text-[28px] md:text-[40px]">
            {t('landing.cta.title')}
          </h2>
          <p className="mx-auto mt-3 max-w-[48ch] text-[17px] font-medium leading-relaxed text-white/85">
            {t('landing.cta.subtitle')}
          </p>
          <div className="mt-8 flex justify-center">
            <Magnetic>
              <Button
                asChild
                className="h-[52px] rounded-2xl bg-white px-10 text-[15px] font-extrabold uppercase tracking-[0.8px] text-[#58a700] shadow-[0_4px_0_0_#e5e5e5] hover:bg-white/90 active:translate-y-[2px] active:shadow-[0_2px_0_0_#e5e5e5]"
              >
                <Link to="/app/scan">{t('landing.hero.startScanning')}</Link>
              </Button>
            </Magnetic>
          </div>
        </div>
      </Reveal>
    </section>
  )
}

function Footer() {
  const { t } = useTranslation()
  return (
    <footer className="border-t-2 border-[#e5e5e5] bg-white px-5 py-10 md:px-[75px]">
      <div className="mx-auto flex max-w-[1152px] flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="flex flex-col items-center gap-1 sm:flex-row sm:gap-3">
          <span className="flex items-center gap-2 text-[20px] font-black text-[#042c60]">
            <NonLaMark size={22} />
            MenuScan
          </span>
          <span className="text-[14px] font-medium text-[#afafaf]">
            {t('footer.rights', { year: new Date().getFullYear() })}
          </span>
        </div>
        <nav className="flex flex-wrap justify-center gap-4 sm:gap-6" aria-label="Footer">
          <a href="#how" className="text-[14px] font-bold text-[#777777] transition-colors hover:text-[#042c60]">
            {t('landing.nav.howItWorks')}
          </a>
          <a href="#partners" className="text-[14px] font-bold text-[#777777] transition-colors hover:text-[#042c60]">
            {t('landing.nav.partners')}
          </a>
          <a href="#reviews" className="text-[14px] font-bold text-[#777777] transition-colors hover:text-[#042c60]">
            {t('landing.nav.reviews')}
          </a>
          <Link to="/auth/login" className="text-[14px] font-bold text-[#777777] transition-colors hover:text-[#042c60]">
            {t('common.login')}
          </Link>
        </nav>
      </div>
    </footer>
  )
}
