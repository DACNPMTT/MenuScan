import { Alert } from '@/shared/components/Alert'
import { Button } from '@/shared/components/Button'
import { Card } from '@/shared/components/Card'
import { Input } from '@/shared/components/Input'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function AuthVerifyPage() {
  useDocumentTitle('Verify access | MenuScan')

  return (
    <section className="route-page route-page--narrow" aria-labelledby="auth-title">
      <p className="eyebrow">Public route</p>
      <h1 id="auth-title">Magic Link verification</h1>
      <p>
        This route is ready for the authenticated flow. Token parsing and API
        verification will be connected in the auth task.
      </p>
      <Card className="route-page__panel">
        <Alert title="Auth foundation ready">
          Public auth routes now share the same layout and design tokens as the
          marketing surface.
        </Alert>
        <Input
          disabled
          helperText="The real token is read from the callback URL later."
          label="Magic Link token"
        />
        <Button disabled type="button">
          Verify token
        </Button>
      </Card>
    </section>
  )
}
