import type { FC } from 'react'

interface CryingMascotProps {
  size?: number
  className?: string
}

export const CryingMascot: FC<CryingMascotProps> = ({ size = 40, className }) => {
  return (
    <svg
      viewBox="0 0 200 250"
      width={size}
      height={size}
      role="img"
      aria-label="Crying MenuScan mascot"
      className={className}
    >
      {/* Body */}
      <g transform="translate(100, 140)">
        <path d="M 0 -85 L 15 -95 L 35 -80 L 50 -90 L 65 -70 L 85 -65 L 75 -45 L 95 -30 L 80 -10 L 100 10 L 85 30 L 95 50 L 75 65 L 85 85 L 50 85 L 40 100 L 20 90 L 0 105 L -20 90 L -40 100 L -50 85 L -85 85 L -75 65 L -95 50 L -85 30 L -100 10 L -80 -10 L -95 -30 L -75 -45 L -85 -65 L -65 -70 L -50 -90 L -35 -80 L -15 -95 Z" fill="#89b653" stroke="#4d6f21" strokeWidth="3" strokeLinejoin="round" />
        <ellipse cx="0" cy="10" rx="65" ry="75" fill="#fde368" stroke="#d5b035" strokeWidth="2" />
      </g>
      <style>
        {`
          @keyframes drop {
            0% { transform: translateY(0); opacity: 1; }
            70% { transform: translateY(20px); opacity: 0; }
            100% { transform: translateY(20px); opacity: 0; }
          }
          .tear-left { animation: drop 1.5s infinite; }
          .tear-right { animation: drop 1.5s infinite 0.75s backwards; }
        `}
      </style>
      
      {/* Sad Face */}
      <g transform="translate(100, 135)">
        <circle cx="-35" cy="15" r="9" fill="#f4a6c0" opacity="0.8" />
        <circle cx="35" cy="15" r="9" fill="#f4a6c0" opacity="0.8" />
        
        {/* Sad eyes (curved downwards) */}
        <path d="M -22 -2 Q -15 -9 -8 -2" stroke="#222" strokeWidth="4" fill="none" strokeLinecap="round" />
        <path d="M 8 -2 Q 15 -9 22 -2" stroke="#222" strokeWidth="4" fill="none" strokeLinecap="round" />
        
        {/* Tears */}
        <g className="tear-left">
          <path d="M -15 2 Q -18 10 -15 15 Q -12 10 -15 2" fill="#60a5fa" />
          <circle cx="-15" cy="15" r="3" fill="#60a5fa" />
        </g>
        
        <g className="tear-right">
          <path d="M 15 2 Q 12 10 15 15 Q 18 10 15 2" fill="#60a5fa" />
          <circle cx="15" cy="15" r="3" fill="#60a5fa" />
        </g>

        {/* Sad mouth */}
        <path d="M -12 15 Q 0 5 12 15" stroke="#222" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      </g>
      {/* Hat */}
      <g transform="translate(100, 55)">
        <ellipse cx="0" cy="35" rx="90" ry="15" fill="#c8a156" />
        <path d="M 0 -55 L -95 35 Q 0 55 95 35 Z" fill="#eed9a1" stroke="#a57f36" strokeWidth="2" strokeLinejoin="round" />
        <path d="M -18 -38 Q 0 -35 18 -38" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
        <path d="M -36 -15 Q 0 -10 36 -15" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
        <path d="M -54 8 Q 0 15 54 8" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
        <path d="M -72 25 Q 0 35 72 25" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
      </g>
    </svg>
  )
}
