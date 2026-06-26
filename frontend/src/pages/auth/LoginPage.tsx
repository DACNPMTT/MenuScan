import { MagicLinkForm } from '@/features/auth/components/MagicLinkForm'

export function LoginPage() {
  return (
    <MagicLinkForm
      heading="Welcome back"
      ctaLabel="Log In"
      alternate={{
        to: '/auth/register',
        prompt: "Don't have an account?",
        label: 'Sign up',
      }}
    />
  )
}
