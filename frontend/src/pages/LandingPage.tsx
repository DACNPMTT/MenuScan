import { Link } from 'react-router-dom'
import { Camera, FileText, Upload } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'
import { Card } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Avatar, AvatarFallback } from '@/shared/components/ui/avatar'
import { LanguageSwitcher } from '@/shared/components/LanguageSwitcher'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

const FEATURE_ICONS = [Upload, Camera, FileText]
const STEP_NUMBERS = ['1', '2', '3', '4']
const STAT_VALUES = ['10K+', '14s', '98%', '24/7']

export function LandingPage() {
  useDocumentTitle('MenuScan')

  return (
    <div className="flex min-h-dvh flex-col bg-canvas font-sans text-ink">
      <TopNav />
      <main className="flex-1">
        <Hero />
        <Stats />
        <Features />
        <HowItWorks />
        <Testimonials />
      </main>
      <Footer />
    </div>
  )
}

function TopNav() {
  const { t } = useTranslation()
  return (
    <header className="flex h-20 items-center justify-between px-5 md:px-[75px]">
      <Link
        to="/"
        className="text-[24px] font-bold tracking-[-0.5px] text-primary-dark"
      >
        MenuScan
      </Link>
      <nav className="hidden items-center gap-10 md:flex" aria-label="Marketing">
        <a href="#features" className="text-[14px] font-bold uppercase tracking-wide text-ink-variant hover:text-ink">
          {t('landing.nav.features')}
        </a>
        <a href="#how-it-works" className="text-[14px] font-bold uppercase tracking-wide text-ink-variant hover:text-ink">
          {t('landing.nav.howItWorks')}
        </a>
      </nav>
      <div className="flex items-center gap-3">
        <LanguageSwitcher />
        <Button
          asChild
          variant="outline"
          className="h-11 rounded-full border-ink px-6 text-ink hover:bg-ink/5"
        >
          <Link to="/auth/login">{t('common.login')}</Link>
        </Button>
        <Button
          asChild
          className="h-11 rounded-full bg-primary px-6 font-bold text-white hover:bg-primary/90"
        >
          <Link to="/auth/register">{t('landing.nav.signup')}</Link>
        </Button>
      </div>
    </header>
  )
}

function Hero() {
  const { t } = useTranslation()
  return (
    <section className="px-5 py-16 md:px-[75px] md:py-24">
      <div className="mx-auto flex max-w-[896px] flex-col items-center text-center">
        <h1 className="text-[40px] font-bold leading-[48px] tracking-[-1px] text-ink md:text-[60px] md:leading-[72px]">
          {t('landing.hero.title')}
        </h1>
        <p className="mt-6 max-w-[672px] text-[16px] leading-[22px] text-ink-variant md:text-[18px]">
          {t('landing.hero.subtitle')}
        </p>
        <div className="mt-8 flex flex-col gap-4 sm:flex-row">
          <Button
            asChild
            className="h-12 rounded-full bg-primary px-8 text-[17px] font-bold text-white hover:bg-primary/90"
          >
            <Link to="/app/scan">{t('landing.hero.startScanning')}</Link>
          </Button>
          <Button
            asChild
            variant="outline"
            className="h-12 rounded-full border-ink px-8 text-[17px] font-bold text-ink hover:bg-ink/5"
          >
            <Link to="/auth/login">{t('common.login')}</Link>
          </Button>
        </div>
      </div>

      <div className="mx-auto mt-12 aspect-[16/7] w-full max-w-[896px] overflow-hidden bg-surface-muted">
        <div className="flex h-full w-full items-center justify-center">
          <div className="h-full w-full bg-[url('MenuScan.jpg')] bg-cover bg-center" />
        </div>
      </div>
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
            <Card
              key={feature.title}
              className="gap-0 rounded-none border-transparent bg-transparent p-0 shadow-none"
            >
              <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
                <Icon className="size-6 text-primary-dark" aria-hidden />
              </div>
              <h3 className="mt-5 text-[20px] font-bold leading-[30px] text-ink">
                {feature.title}
              </h3>
              <p className="mt-2 text-[16px] leading-[22px] text-ink-variant">
                {feature.body}
              </p>
            </Card>
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
    <section
      id="how-it-works"
      className="bg-surface-muted px-5 py-16 md:px-[75px] md:py-24"
    >
      <div className="mx-auto max-w-[1152px]">
        <h2 className="text-center text-[36px] font-bold leading-[44px] tracking-[-0.75px] text-ink md:text-[48px]">
          {t('landing.how.title')}
        </h2>
        <div className="relative mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="absolute left-0 right-0 top-7 hidden h-px bg-hairline lg:block" />
          {steps.map((step, index) => (
            <div key={step.title} className="relative flex flex-col items-center text-center">
              <div className="flex size-14 items-center justify-center rounded-full border border-hairline bg-canvas text-[24px] font-bold text-primary-dark">
                {STEP_NUMBERS[index] ?? index + 1}
              </div>
              <h3 className="mt-4 text-[20px] font-bold leading-[30px] text-ink">
                {step.title}
              </h3>
              <p className="mt-1 text-[14px] leading-[21px] text-ink-variant">
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Footer() {
  const { t } = useTranslation()
  return (
    <footer className="bg-ink px-5 py-10 text-white md:px-[75px]">
      <div className="mx-auto flex max-w-[1152px] flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="flex flex-col items-center gap-1 sm:flex-row sm:gap-3">
          <span className="text-[20px] font-bold">MenuScan</span>
          <span className="text-[14px] text-white/70">
            {t('footer.rights', { year: 2024 })}
          </span>
        </div>
        <nav className="flex gap-6" aria-label="Footer">
          <a href="#features" className="text-[14px] text-white/70 hover:text-white">
            {t('landing.nav.features')}
          </a>
          <a href="#how-it-works" className="text-[14px] text-white/70 hover:text-white">
            {t('landing.nav.howItWorks')}
          </a>
          <Link to="/auth/login" className="text-[14px] text-white/70 hover:text-white">
            {t('common.login')}
          </Link>
        </nav>
      </div>
    </footer>
  )
}

function Stats() {
  const { t } = useTranslation()
  const labels = t('landing.stats.labels', { returnObjects: true }) as string[]
  return (
    <section className="bg-primary px-5 py-16 text-white md:px-[75px] md:py-20">
      <div className="mx-auto max-w-[1152px]">
        <Badge className="mb-6 rounded-full bg-white/15 px-3 py-1 text-[12px] text-white hover:bg-white/20">
          {t('landing.stats.badge')}
        </Badge>
        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          {STAT_VALUES.map((value, index) => (
            <div key={value}>
              <div className="text-[40px] font-bold leading-none tracking-[-0.5px] md:text-[56px]">
                {value}
              </div>
              <div className="mt-2 text-[14px] text-white/80">{labels[index]}</div>
            </div>
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
        <h2 className="text-center text-[36px] font-bold leading-[44px] tracking-[-0.75px] text-ink md:text-[48px] md:leading-[56px]">
          {t('landing.testimonials.title')}
        </h2>
        <p className="mt-3 text-center text-[16px] leading-[22px] text-ink-variant">
          {t('landing.testimonials.subtitle')}
        </p>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {items.map((item) => (
            <Card key={item.name} className="gap-0 rounded-none border border-hairline bg-canvas p-8 shadow-none">
              <p className="text-[16px] leading-[22px] text-ink">&ldquo;{item.quote}&rdquo;</p>
              <div className="mt-6 flex items-center gap-3">
                <Avatar>
                  <AvatarFallback className="rounded-full bg-surface-muted text-[14px] font-bold text-primary-dark">
                    {item.initials}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <div className="text-[14px] font-bold text-ink">{item.name}</div>
                  <div className="text-[14px] text-ink-variant">{item.role}</div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
