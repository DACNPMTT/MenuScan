interface NonLaMarkProps {
  size?: number
  className?: string
}

/**
 * Vietnamese conical hat (nón lá) brand mark rendered as inline SVG. Solid
 * fills only (no gradients). This is the brand mark reused across the landing
 * page, auth chrome and favicon. Parents animate it via `motion` when needed.
 */
export function MenuScanLogo({ size = 40, className }: NonLaMarkProps) {
  return (
    <svg
      viewBox="0 0 200 250"
      width={size}
      height={size}
      role="img"
      aria-label="MenuScan logo"
      className={className}
    >
      {/* Hat */}
      <g transform="translate(100, 55)">
        <ellipse cx="0" cy="35" rx="90" ry="15" fill="#c8a156" />
        <path d="M 0 -55 L -95 35 Q 0 55 95 35 Z" fill="#eed9a1" stroke="#a57f36" strokeWidth="2" strokeLinejoin="round" />
        <path d="M -18 -38 Q 0 -35 18 -38" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
        <path d="M -36 -15 Q 0 -10 36 -15" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
        <path d="M -54 8 Q 0 15 54 8" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
        <path d="M -72 25 Q 0 35 72 25" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
      </g>
      {/* Body */}
      <g transform="translate(100, 140)">
        <path d="M 0 -85 L 15 -95 L 35 -80 L 50 -90 L 65 -70 L 85 -65 L 75 -45 L 95 -30 L 80 -10 L 100 10 L 85 30 L 95 50 L 75 65 L 85 85 L 50 85 L 40 100 L 20 90 L 0 105 L -20 90 L -40 100 L -50 85 L -85 85 L -75 65 L -95 50 L -85 30 L -100 10 L -80 -10 L -95 -30 L -75 -45 L -85 -65 L -65 -70 L -50 -90 L -35 -80 L -15 -95 Z" fill="#89b653" stroke="#4d6f21" strokeWidth="3" strokeLinejoin="round" />
        <ellipse cx="0" cy="10" rx="65" ry="75" fill="#fde368" stroke="#d5b035" strokeWidth="2" />
      </g>
      {/* Face */}
      <g transform="translate(100, 135)">
        <circle cx="-35" cy="15" r="9" fill="#f4a6c0" opacity="0.8" />
        <circle cx="35" cy="15" r="9" fill="#f4a6c0" opacity="0.8" />
        <path d="M -22 -5 Q -15 -13 -8 -5" stroke="#222" strokeWidth="4" fill="none" strokeLinecap="round" />
        <path d="M 8 -5 Q 15 -13 22 -5" stroke="#222" strokeWidth="4" fill="none" strokeLinecap="round" />
        <path d="M -15 5 Q 0 35 15 5 Z" fill="#c1432e" stroke="#222" strokeWidth="2.5" strokeLinejoin="round" />
        <path d="M -8 15 Q 0 25 8 15 Z" fill="#ffb6c1" />
      </g>
    </svg>
  )
}
