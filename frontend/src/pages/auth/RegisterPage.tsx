import { MagicLinkForm } from '@/features/auth/components/MagicLinkForm'

export function RegisterPage() {
  return (
    <MagicLinkForm
      heading="Create your account"
      ctaLabel="Sign Up"
      alternate={{
        to: '/auth/login',
        prompt: 'Already have an account?',
        label: 'Log in',
      }}
    />
  )
}
