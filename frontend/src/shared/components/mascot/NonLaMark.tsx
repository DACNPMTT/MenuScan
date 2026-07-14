interface NonLaMarkProps {
  size?: number
  className?: string
}

/**
 * Vietnamese conical hat (nón lá) brand mark rendered as inline SVG. Solid
 * fills only (no gradients). This is the brand mark reused across the landing
 * page, auth chrome and favicon. Parents animate it via `motion` when needed.
 */
export function NonLaMark({ size = 40, className }: NonLaMarkProps) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      role="img"
      aria-label="MenuScan logo"
      className={className}
    >
      {/* Hat cone — apex top-center, wide curved brim */}
      <path d="M32 7 L9 49 Q32 54 55 49 Z" fill="#e8c170" />
      {/* Upper-left highlight */}
      <path d="M32 10 L15 46 Q25 49 31 48 Z" fill="#f3d98f" opacity="0.65" />
      {/* Woven arc lines (straw weave) */}
      <path d="M21 39 Q32 42 43 39" stroke="#c08a2e" strokeWidth="1.1" fill="none" opacity="0.45" />
      <path d="M24 31 Q32 33 40 31" stroke="#c08a2e" strokeWidth="1.1" fill="none" opacity="0.4" />
      <path d="M27 23 Q32 25 37 23" stroke="#c08a2e" strokeWidth="1" fill="none" opacity="0.35" />
      {/* Apex tip */}
      <circle cx="32" cy="8" r="1.7" fill="#c08a2e" />
      {/* Chin strap */}
      <path d="M22 50 Q32 60 42 50" stroke="#8b5e3c" strokeWidth="1.7" fill="none" strokeLinecap="round" opacity="0.8" />
    </svg>
  )
}
