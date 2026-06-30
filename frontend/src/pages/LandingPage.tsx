import { Link } from 'react-router-dom'
import { Camera, FileText, Upload } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Card } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Avatar, AvatarFallback } from '@/shared/components/ui/avatar'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

const features = [
  {
    icon: Upload,
    title: 'Upload image',
    body: 'Drag and drop or select a photo of any restaurant menu.',
  },
  {
    icon: Camera,
    title: 'Scan camera',
    body: "Use your device's camera to capture a menu directly in real-time.",
  },
  {
    icon: FileText,
    title: 'Extract data',
    body: 'Instantly receive structured JSON with items, prices, and categories.',
  },
]

const steps = [
  { n: '1', title: 'Upload', body: 'Provide menu image.' },
  { n: '2', title: 'AI Analysis', body: 'Engine processes image.' },
  { n: '3', title: 'Extraction', body: 'Structure data mapped.' },
  { n: '4', title: 'Review', body: 'Export or edit results.' },
]

const stats = [
  { value: '10K+', label: 'Menus digitized' },
  { value: '14s', label: 'Avg. processing' },
  { value: '98%', label: 'Field accuracy' },
  { value: '24/7', label: 'Always available' },
]

const testimonials = [
  { quote: 'MenuScan giảm 80% thời gian nhập menu cho quán mình.', name: 'Minh Anh', role: 'Quản lý · Cafe Sài Gòn', initials: 'MA' },
  { quote: 'OCR nhận diện tốt cả menu tiếng Việt có dấu, ít phải sửa.', name: 'Hoàng Nguyên', role: 'Chủ · Phở 24', initials: 'HN' },
  { quote: 'Có dữ liệu JSON ngay sau khi upload, tích hợp rất nhanh.', name: 'Trần Vy', role: 'Dev · FoodApp', initials: 'TV' },
]

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
          Features
        </a>
        <a href="#how-it-works" className="text-[14px] font-bold uppercase tracking-wide text-ink-variant hover:text-ink">
          How it works
        </a>
      </nav>
      <div className="flex items-center gap-3">
        <Button
          asChild
          variant="outline"
          className="h-11 rounded-full border-ink px-6 text-ink hover:bg-ink/5"
        >
          <Link to="/auth/login">Log in</Link>
        </Button>
        <Button
          asChild
          className="h-11 rounded-full bg-primary px-6 font-bold text-white hover:bg-primary/90"
        >
          <Link to="/auth/register">Sign up</Link>
        </Button>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="px-5 py-16 md:px-[75px] md:py-24">
      <div className="mx-auto flex max-w-[896px] flex-col items-center text-center">
        <h1 className="text-[40px] font-bold leading-[48px] tracking-[-1px] text-ink md:text-[60px] md:leading-[72px]">
          Turn menu photos into structured data
        </h1>
        <p className="mt-6 max-w-[672px] text-[16px] leading-[22px] text-ink-variant md:text-[18px]">
          Automatically extract dishes, prices, descriptions, and dietary
          information from any physical menu image in seconds.
        </p>
        <div className="mt-8 flex flex-col gap-4 sm:flex-row">
          <Button
            asChild
            className="h-12 rounded-full bg-primary px-8 text-[17px] font-bold text-white hover:bg-primary/90"
          >
            <Link to="/app/scan">Start scanning</Link>
          </Button>
          <Button
            asChild
            variant="outline"
            className="h-12 rounded-full border-ink px-8 text-[17px] font-bold text-ink hover:bg-ink/5"
          >
            <Link to="/auth/login">Log in</Link>
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
  return (
    <section id="features" className="px-5 py-16 md:px-[75px] md:py-20">
      <div className="mx-auto grid max-w-[1152px] gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((feature) => (
          <Card
            key={feature.title}
            className="gap-0 rounded-none border-transparent bg-transparent p-0 shadow-none"
          >
            <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
              <feature.icon className="size-6 text-primary-dark" aria-hidden />
            </div>
            <h3 className="mt-5 text-[20px] font-bold leading-[30px] text-ink">
              {feature.title}
            </h3>
            <p className="mt-2 text-[16px] leading-[22px] text-ink-variant">
              {feature.body}
            </p>
          </Card>
        ))}
      </div>
    </section>
  )
}

function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="bg-surface-muted px-5 py-16 md:px-[75px] md:py-24"
    >
      <div className="mx-auto max-w-[1152px]">
        <h2 className="text-center text-[36px] font-bold leading-[44px] tracking-[-0.75px] text-ink md:text-[48px]">
          How it Works
        </h2>
        <div className="relative mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="absolute left-0 right-0 top-7 hidden h-px bg-hairline lg:block" />
          {steps.map((step) => (
            <div key={step.n} className="relative flex flex-col items-center text-center">
              <div className="flex size-14 items-center justify-center rounded-full border border-hairline bg-canvas text-[24px] font-bold text-primary-dark">
                {step.n}
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
  return (
    <footer className="bg-ink px-5 py-10 text-white md:px-[75px]">
      <div className="mx-auto flex max-w-[1152px] flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="flex flex-col items-center gap-1 sm:flex-row sm:gap-3">
          <span className="text-[20px] font-bold">MenuScan</span>
          <span className="text-[14px] text-white/70">
            © 2024 MenuScan. All rights reserved.
          </span>
        </div>
        <nav className="flex gap-6" aria-label="Footer">
          <a href="#features" className="text-[14px] text-white/70 hover:text-white">
            Features
          </a>
          <a href="#how-it-works" className="text-[14px] text-white/70 hover:text-white">
            How it works
          </a>
          <Link to="/auth/login" className="text-[14px] text-white/70 hover:text-white">
            Log in
          </Link>
        </nav>
      </div>
    </footer>
  )
}

function Stats() {
  return (
    <section className="bg-primary px-5 py-16 text-white md:px-[75px] md:py-20">
      <div className="mx-auto max-w-[1152px]">
        <Badge className="mb-6 rounded-full bg-white/15 px-3 py-1 text-[12px] text-white hover:bg-white/20">
          By the numbers
        </Badge>
        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label}>
              <div className="text-[40px] font-bold leading-none tracking-[-0.5px] md:text-[56px]">
                {stat.value}
              </div>
              <div className="mt-2 text-[14px] text-white/80">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Testimonials() {
  return (
    <section id="testimonials" className="px-5 py-16 md:px-[75px] md:py-24">
      <div className="mx-auto max-w-[1152px]">
        <h2 className="text-center text-[36px] font-bold leading-[44px] tracking-[-0.75px] text-ink md:text-[48px] md:leading-[56px]">
          Khách hàng nói gì
        </h2>
        <p className="mt-3 text-center text-[16px] leading-[22px] text-ink-variant">
          Người dùng trên khắp nơi đang số hóa menu với MenuScan.
        </p>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {testimonials.map((t) => (
            <Card key={t.name} className="gap-0 rounded-none border border-hairline bg-canvas p-8 shadow-none">
              <p className="text-[16px] leading-[22px] text-ink">&ldquo;{t.quote}&rdquo;</p>
              <div className="mt-6 flex items-center gap-3">
                <Avatar>
                  <AvatarFallback className="rounded-full bg-surface-muted text-[14px] font-bold text-primary-dark">
                    {t.initials}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <div className="text-[14px] font-bold text-ink">{t.name}</div>
                  <div className="text-[14px] text-ink-variant">{t.role}</div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
