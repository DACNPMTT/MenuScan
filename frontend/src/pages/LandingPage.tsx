import { Link } from 'react-router-dom'
import { Camera, FileText, ScanText, Sparkles, Upload } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { Button } from '@/shared/components/ui/button'
import { Card } from '@/shared/components/ui/card'
import { Avatar, AvatarFallback } from '@/shared/components/ui/avatar'
import { LanguageSwitcher } from '@/shared/components/LanguageSwitcher'
import { IconBadge } from '@/shared/components/IconBadge'
import { Reveal } from '@/shared/components/motion/Reveal'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { DotGrid } from '@/shared/components/rb/DotGrid'
import { BlurText } from '@/shared/components/rb/BlurText'
import { TiltCard } from '@/shared/components/rb/TiltCard'
import { AnimatedCounter } from '@/shared/components/rb/AnimatedCounter'
import { ScrollFloat } from '@/shared/components/rb/ScrollFloat'
import { Magnetic } from '@/shared/components/rb/Magnetic'
import { GuardedHero3D } from '@/shared/components/three/GuardedHero3D'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useAuth } from '@/app/providers/AuthProvider'

const FEATURE_ICONS = [Upload, Camera, FileText]
const STEP_NUMBERS = ['1', '2', '3', '4']

// Marketing stats. Three animate (numeric), one is static text.
const STATS: Array<{ count?: number; value?: string; suffix?: string }> = [
  { count: 10, suffix: 'K+' },
  { count: 14, suffix: 's' },
  { count: 98, suffix: '%' },
  { value: '24/7' },
]

const EASE = [0.22, 1, 0.36, 1] as const

export function LandingPage() {
  useDocumentTitle('MenuScan')

  return (
    <PageTransition>
      <div className="flex min-h-dvh flex-col bg-app-bg font-sans text-ink">
        <TopNav />
        <main className="flex-1">
          <Hero />
          <ProductPreview />
          <Stats />
          <Features />
          <HowItWorks />
          <Testimonials />
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
      className="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-border bg-surface/70 px-5 backdrop-blur-xl md:px-[75px]"
    >
      <Link to="/" className="flex items-center gap-2.5" aria-label="MenuScan home">
        <span className="flex size-9 items-center justify-center rounded-2xl bg-primary text-white shadow-2 shadow-primary/40">
          <ScanText className="size-5" aria-hidden />
        </span>
        <span className="text-[22px] font-extrabold tracking-tight text-ink">MenuScan</span>
      </Link>
      <nav className="hidden items-center gap-8 md:flex" aria-label="Marketing">
        <a href="#features" className="text-[14px] font-semibold text-ink-variant transition-colors hover:text-primary">
          {t('landing.nav.features')}
        </a>
        <a href="#how-it-works" className="text-[14px] font-semibold text-ink-variant transition-colors hover:text-primary">
          {t('landing.nav.howItWorks')}
        </a>
      </nav>
      <div className="flex items-center gap-3">
        <LanguageSwitcher />
        {user ? (
          <Magnetic>
            <Button asChild>
              <Link to="/app">{t('landing.nav.goToApp')}</Link>
            </Button>
          </Magnetic>
        ) : (
          <>
            <Button asChild variant="outline">
              <Link to="/auth/login">{t('common.login')}</Link>
            </Button>
            <Magnetic>
              <Button asChild>
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
  return (
    <section className="relative overflow-hidden px-5 py-16 md:px-[75px] md:py-24">
      {/* Decorative dot grid + soft solid blobs — NO gradient. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute inset-0 opacity-60">
          <DotGrid color="rgba(37, 99, 235, 0.14)" />
        </div>
        <div className="absolute left-1/2 top-[-18%] h-[420px] w-[640px] max-w-[120vw] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute right-[-8%] top-[24%] h-[300px] w-[300px] rounded-full bg-accent/20 blur-3xl" />
      </div>

      <div className="mx-auto grid max-w-[1152px] grid-cols-1 items-center gap-12 lg:grid-cols-2">
        {/* Text column */}
        <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-1.5 text-[13px] font-bold text-primary shadow-1"
          >
            <Sparkles className="size-4 text-accent" aria-hidden />
            {t('landing.hero.badge')}
          </motion.span>

          <BlurText
            as="h1"
            text={t('landing.hero.title')}
            className="max-w-[16ch] text-[40px] font-extrabold leading-[1.1] tracking-tight text-ink md:text-[52px]"
          />

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE, delay: 0.2 }}
            className="mt-6 max-w-[672px] text-[16px] leading-[26px] text-ink-variant md:text-[18px] md:leading-[28px]"
          >
            {t('landing.hero.subtitle')}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE, delay: 0.32 }}
            className="mt-9 flex flex-col gap-4 sm:flex-row"
          >
            <Magnetic>
              <Button asChild size="lg" className="h-14 px-10 text-[18px]">
                <Link to="/app/scan">{t('landing.hero.startScanning')}</Link>
              </Button>
            </Magnetic>
            {!user && (
              <Magnetic>
                <Button asChild variant="outline" size="lg" className="h-14 px-8 text-[17px]">
                  <Link to="/auth/login">{t('common.login')}</Link>
                </Button>
              </Magnetic>
            )}
          </motion.div>
        </div>

        {/* 3D visual column — lazy, never blocks first paint. */}
        <div className="relative flex items-center justify-center">
          <GuardedHero3D />
        </div>
      </div>
    </section>
  )
}

function ProductPreview() {
  const { t } = useTranslation()
  return (
    <section className="px-5 py-8 md:px-[75px] md:py-12">
      <div className="relative mx-auto w-full max-w-[960px]">
        <ScrollFloat amount={28}>
          <TiltCard max={6} className="rounded-[28px]">
            <div className="overflow-hidden rounded-[28px] border border-border bg-surface shadow-3">
              <img
                src="/MenuScan.jpg"
                alt={t('landing.hero.imageAlt')}
                width={1400}
                height={760}
                className="block w-full"
              />
            </div>
          </TiltCard>
        </ScrollFloat>
      </div>
    </section>
  )
}

function Stats() {
  const { t } = useTranslation()
  const labels = t('landing.stats.labels', { returnObjects: true }) as string[]
  return (
    <section className="px-5 py-16 md:px-[75px] md:py-20">
      <Reveal className="mx-auto max-w-[1152px]">
        <div className="overflow-hidden rounded-3xl bg-primary px-6 py-12 shadow-3 shadow-primary/30 md:px-12">
          <div className="mx-auto max-w-[960px]">
            <motion.span
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.3, ease: EASE }}
              className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-[12px] font-bold text-white"
            >
              {t('landing.stats.badge')}
            </motion.span>
            <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
              {STATS.map((stat, index) => (
                <div
                  key={index}
                  className="rounded-2xl border border-white/15 bg-white/10 p-5 backdrop-blur-sm"
                >
                  <div className="text-[40px] font-extrabold leading-none tracking-tight text-white md:text-[52px]">
                    {typeof stat.count === 'number' ? (
                      <>
                        <AnimatedCounter to={stat.count} duration={1.8} />
                        {stat.suffix}
                      </>
                    ) : (
                      stat.value
                    )}
                  </div>
                  <div className="mt-2 text-[14px] text-white/80">{labels[index]}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  )
}

function Features() {
  const { t } = useTranslation()
  const features = t('landing.features', { returnObjects: true }) as Array<{
    title: string
    body: string
  }>
  return (
    <section id="features" className="px-5 py-16 md:px-[75px] md:py-20">
      <div className="mx-auto grid max-w-[1152px] gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((feature, index) => {
          const Icon = FEATURE_ICONS[index] ?? Upload
          return (
            <Reveal key={feature.title} delay={index * 0.08}>
              <TiltCard max={5}>
                <Card className="h-full gap-4 rounded-2xl p-6">
                  <IconBadge icon={Icon} size="md" />
                  <h3 className="text-[20px] font-bold leading-tight text-ink">
                    {feature.title}
                  </h3>
                  <p className="text-[15px] leading-relaxed text-ink-variant">
                    {feature.body}
                  </p>
                </Card>
              </TiltCard>
            </Reveal>
          )
        })}
      </div>
    </section>
  )
}

function HowItWorks() {
  const { t } = useTranslation()
  const steps = t('landing.how.steps', { returnObjects: true }) as Array<{
    title: string
    body: string
  }>
  return (
    <section id="how-it-works" className="bg-panel px-5 py-16 md:px-[75px] md:py-24">
      <div className="mx-auto max-w-[1152px]">
        <Reveal>
          <h2 className="text-center text-[34px] font-extrabold leading-tight tracking-tight text-ink md:text-[46px]">
            {t('landing.how.title')}
          </h2>
        </Reveal>
        <div className="relative mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="absolute left-0 right-0 top-7 hidden h-px bg-border lg:block" />
          {steps.map((step, index) => (
            <Reveal key={step.title} delay={index * 0.08} className="relative flex flex-col items-center text-center">
              <div className="flex size-14 items-center justify-center rounded-2xl bg-surface text-[22px] font-extrabold text-primary shadow-2 ring-1 ring-primary/20">
                {STEP_NUMBERS[index] ?? index + 1}
              </div>
              <h3 className="mt-4 text-[19px] font-bold leading-tight text-ink">
                {step.title}
              </h3>
              <p className="mt-1 text-[14px] leading-relaxed text-ink-variant">
                {step.body}
              </p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Testimonials() {
  const { t } = useTranslation()
  const items = t('landing.testimonials.items', { returnObjects: true }) as Array<{
    quote: string
    name: string
    role: string
    initials: string
  }>
  return (
    <section id="testimonials" className="px-5 py-16 md:px-[75px] md:py-24">
      <div className="mx-auto max-w-[1152px]">
        <Reveal>
          <h2 className="text-center text-[34px] font-extrabold leading-tight tracking-tight text-ink md:text-[46px]">
            {t('landing.testimonials.title')}
          </h2>
          <p className="mt-3 text-center text-[16px] leading-relaxed text-ink-variant">
            {t('landing.testimonials.subtitle')}
          </p>
        </Reveal>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {items.map((item, index) => (
            <Reveal key={item.name} delay={index * 0.1}>
              <Card className="h-full gap-6 p-8">
                <p className="text-[16px] leading-relaxed text-ink">&ldquo;{item.quote}&rdquo;</p>
                <div className="flex items-center gap-3">
                  <Avatar>
                    <AvatarFallback className="rounded-full bg-primary/10 text-[14px] font-bold text-primary">
                      {item.initials}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="text-[14px] font-bold text-ink">{item.name}</div>
                    <div className="text-[14px] text-ink-variant">{item.role}</div>
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
    <section className="px-5 py-20 md:px-[75px] md:py-28">
      <Reveal className="mx-auto max-w-[1152px]">
        <div className="overflow-hidden rounded-3xl bg-primary px-6 py-16 text-center shadow-3 shadow-primary/30 md:px-12 md:py-20">
          <h2 className="mx-auto max-w-[24ch] text-[28px] font-extrabold leading-tight tracking-tight text-white md:text-[40px]">
            {t('landing.hero.subtitle')}
          </h2>
          <div className="mt-8 flex justify-center">
            <Magnetic>
              <Button
                asChild
                size="lg"
                className="h-14 bg-white px-10 text-[18px] text-primary hover:bg-white/90"
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
    <footer className="bg-ink px-5 py-10 text-white md:px-[75px]">
      <div className="mx-auto flex max-w-[1152px] flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="flex flex-col items-center gap-1 sm:flex-row sm:gap-3">
          <span className="flex items-center gap-2 text-[20px] font-extrabold">
            <ScanText className="size-5" aria-hidden />
            MenuScan
          </span>
          <span className="text-[14px] text-white/60">
            {t('footer.rights', { year: new Date().getFullYear() })}
          </span>
        </div>
        <nav className="flex gap-6" aria-label="Footer">
          <a href="#features" className="text-[14px] text-white/60 transition-colors hover:text-white">
            {t('landing.nav.features')}
          </a>
          <a href="#how-it-works" className="text-[14px] text-white/60 transition-colors hover:text-white">
            {t('landing.nav.howItWorks')}
          </a>
          <Link to="/auth/login" className="text-[14px] text-white/60 transition-colors hover:text-white">
            {t('common.login')}
          </Link>
        </nav>
      </div>
    </footer>
  )
}
