type SpinnerProps = {
  label?: string
}

export function Spinner({ label = 'Loading' }: SpinnerProps) {
  return (
    <span className="spinner" role="status">
      <span className="spinner__mark" aria-hidden="true" />
      <span className="visually-hidden">{label}</span>
    </span>
  )
}
