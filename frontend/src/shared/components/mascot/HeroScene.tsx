import { useState, useEffect } from 'react'
import { motion } from 'motion/react'

export function HeroScene() {
  const [step, setStep] = useState(1)

  useEffect(() => {
    const timer = setInterval(() => {
      setStep((prev) => (prev === 5 ? 1 : prev + 1))
    }, 4500)
    return () => clearInterval(timer)
  }, [])

  // Các đường Path cho cánh tay uốn éo mềm mại (Morphing)
  const getRightArmPath = () => {
    switch (step) {
      case 1: return "M 220 190 Q 250 200 190 230" // Cầm Menu
      case 2: return "M 220 190 Q 260 140 220 120"  // Gãi đầu
      case 3: return "M 220 190 Q 250 250 230 270" // Thả lỏng 
      case 4: return "M 220 190 Q 200 230 150 220" // Bấm bấm điện thoại
      case 5: return "M 220 190 Q 270 200 260 140" // Thumbs up đưa ra ngoài
      default: return "M 220 190 Q 250 250 230 270"
    }
  }

  const getLeftArmPath = () => {
    switch (step) {
      case 1: return "M 80 190 Q 40 140 80 120"    // Gãi đầu
      case 2: return "M 80 190 Q 50 230 110 220" // Cầm Điện Thoại Dịch
      case 3: return "M 80 190 Q 50 250 70 270"  // Thả lỏng
      case 4: return "M 80 190 Q 60 250 130 220" // Cầm Điện thoại lên web
      case 5: return "M 80 190 Q 30 220 100 240"  // Đưa điện thoại quét
      default: return "M 80 190 Q 50 250 70 270"
    }
  }

  const getPhoneTransform = () => {
    switch (step) {
      case 2: return { x: 75, y: 190, rotate: 15, scale: 1, opacity: 1 }
      case 4: return { x: 100, y: 190, rotate: 10, scale: 1, opacity: 1 }
      case 5: return { x: 65, y: 195, rotate: -20, scale: 1.1, opacity: 1 }
      default: return { x: 80, y: 250, rotate: 0, scale: 0.8, opacity: 0 } 
    }
  }

  const isConfused = step === 1 || step === 2
  const isIdea = step === 3
  const isHappy = step === 4 || step === 5

  return (
    <div className="relative w-full max-w-3xl mx-auto flex flex-col items-center">
      
      {/* Màn hình chiếu phim hoạt hình 2D (Lớp nền trong suốt hoàn toàn) */}
      <div className="relative w-full aspect-square flex items-center justify-center overflow-visible">
        
        {/* Glow phát sáng nhẹ phía sau nhân vật để làm nổi bật */}
        <div className="absolute left-1/2 top-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-tr from-[#89b653]/20 to-[#ffc800]/20 blur-3xl" />

        <svg viewBox="0 0 300 300" className="w-full h-full drop-shadow-[0_10px_20px_rgba(0,0,0,0.1)] overflow-visible relative z-10" role="img">
          
          {/* CÁI BÀN GỖ (Floating Platform) - Nằm dưới cùng để không che mất nhân vật */}
          <g transform="translate(150, 260)">
            <rect x="-100" y="0" width="200" height="20" fill="#d89851" stroke="#a06e3d" strokeWidth="4" rx="10" />
            <path d="M -90 20 L 90 20 Q 95 20 95 25 L 95 35 Q 95 40 90 40 L -90 40 Q -95 40 -95 35 L -95 25 Q -95 20 -90 20 Z" fill="#a06e3d" />
          </g>

          {/* NHÂN VẬT SẦU RIÊNG (Morphing & Floating) */}
          <motion.g 
            animate={{ y: [0, -4, 0] }} 
            transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          >
            {/* Lớp áo gai xanh (Green Spiky Shell) */}
            <g transform="translate(150, 160)">
              <path 
                d="M 0 -85 L 15 -95 L 35 -80 L 50 -90 L 65 -70 L 85 -65 L 75 -45 L 95 -30 L 80 -10 L 100 10 L 85 30 L 95 50 L 75 65 L 85 85 L 50 85 L 40 100 L 20 90 L 0 105 L -20 90 L -40 100 L -50 85 L -85 85 L -75 65 L -95 50 L -85 30 L -100 10 L -80 -10 L -95 -30 L -75 -45 L -85 -65 L -65 -70 L -50 -90 L -35 -80 L -15 -95 Z" 
                fill="#89b653" stroke="#4d6f21" strokeWidth="3" strokeLinejoin="round" 
              />
              {/* Lớp ruột vàng (Yellow Smooth Body) */}
              <ellipse cx="0" cy="10" rx="65" ry="75" fill="#fde368" stroke="#d5b035" strokeWidth="2" />
            </g>

            {/* NÓN LÁ */}
            <g transform="translate(150, 65)">
              <ellipse cx="0" cy="35" rx="90" ry="15" fill="#c8a156" />
              <path d="M 0 -55 L -95 35 Q 0 55 95 35 Z" fill="#eed9a1" stroke="#a57f36" strokeWidth="2" strokeLinejoin="round" />
              <path d="M -18 -38 Q 0 -35 18 -38" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
              <path d="M -36 -15 Q 0 -10 36 -15" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
              <path d="M -54 8 Q 0 15 54 8" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
              <path d="M -72 25 Q 0 35 72 25" stroke="#a57f36" strokeWidth="1.5" fill="none" opacity="0.4" />
            </g>

            {/* KHUÔN MẶT */}
            <g transform="translate(150, 155)">
              {/* Má hồng */}
              <circle cx="-35" cy="15" r="9" fill="#f4a6c0" opacity="0.8" />
              <circle cx="35" cy="15" r="9" fill="#f4a6c0" opacity="0.8" />

              {/* Bối rối (Confused) */}
              <motion.g initial={false} animate={{ opacity: isConfused ? 1 : 0 }} transition={{ duration: 0.3 }}>
                <ellipse cx="-15" cy="-5" rx="5" ry="7" fill="#222" />
                <ellipse cx="15" cy="-5" rx="5" ry="7" fill="#222" />
                <circle cx="-13" cy="-7" r="2" fill="#fff" />
                <circle cx="17" cy="-7" r="2" fill="#fff" />
                <path d="M -25 -15 L -5 -10" stroke="#222" strokeWidth="3" strokeLinecap="round" />
                <path d="M 5 -10 L 25 -15" stroke="#222" strokeWidth="3" strokeLinecap="round" />
                <path d="M -10 20 Q 0 10 10 20" stroke="#222" strokeWidth="3" fill="none" strokeLinecap="round" />
              </motion.g>

              {/* Ngạc nhiên (Idea) */}
              <motion.g initial={false} animate={{ opacity: isIdea ? 1 : 0 }} transition={{ duration: 0.3 }}>
                <circle cx="-15" cy="-5" r="8" fill="#fff" stroke="#222" strokeWidth="2.5" />
                <circle cx="15" cy="-5" r="8" fill="#fff" stroke="#222" strokeWidth="2.5" />
                <circle cx="-15" cy="-5" r="3" fill="#222" />
                <circle cx="15" cy="-5" r="3" fill="#222" />
                <ellipse cx="0" cy="15" rx="6" ry="9" fill="#222" />
              </motion.g>

              {/* Vui vẻ (Happy) */}
              <motion.g initial={false} animate={{ opacity: isHappy ? 1 : 0 }} transition={{ duration: 0.3 }}>
                <path d="M -22 -5 Q -15 -13 -8 -5" stroke="#222" strokeWidth="4" fill="none" strokeLinecap="round" />
                <path d="M 8 -5 Q 15 -13 22 -5" stroke="#222" strokeWidth="4" fill="none" strokeLinecap="round" />
                <path d="M -15 5 Q 0 35 15 5 Z" fill="#c1432e" stroke="#222" strokeWidth="2.5" strokeLinejoin="round" />
                <path d="M -8 15 Q 0 25 8 15 Z" fill="#ffb6c1" />
              </motion.g>
            </g>

            {/* HAI CÁNH TAY */}
            <g transform="translate(0, -20)">
              <motion.path 
                animate={{ d: getLeftArmPath() }} transition={{ duration: 0.6, ease: "easeInOut" }}
                stroke="#4d6f21" strokeWidth="16" fill="none" strokeLinecap="round" 
              />
              <motion.path 
                animate={{ d: getRightArmPath() }} transition={{ duration: 0.6, ease: "easeInOut" }}
                stroke="#4d6f21" strokeWidth="16" fill="none" strokeLinecap="round" 
              />
              <motion.path 
                animate={{ d: getLeftArmPath() }} transition={{ duration: 0.6, ease: "easeInOut" }}
                stroke="#89b653" strokeWidth="10" fill="none" strokeLinecap="round" 
              />
              <motion.path 
                animate={{ d: getRightArmPath() }} transition={{ duration: 0.6, ease: "easeInOut" }}
                stroke="#89b653" strokeWidth="10" fill="none" strokeLinecap="round" 
              />

              {/* BÀN TAY PHẢI SỐ 1 (Thumbs up - Nút Like gắn liền cổ tay) */}
              <g transform="translate(252, 106)">
                <motion.g 
                  initial={false} 
                  animate={{ opacity: step === 5 ? 1 : 0 }} 
                  transition={{ duration: 0.3, delay: step === 5 ? 0.3 : 0 }}
                  style={{ x: 0, y: 0 }}
                >
                  {/* Nắm đấm (3 ngón tay gập) - Không có viền dưới cùng để khớp nối mượt mà vào lõi tay màu xanh */}
                  <path d="M 0 34 L 2 10 L 16 10 A 4 4 0 0 1 16 18 A 4 4 0 0 1 16 26 A 4 4 0 0 1 16 34" fill="#89b653" stroke="#4d6f21" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                  {/* Ngón cái chỉ lên (Like) */}
                  <path d="M 10 14 L 10 2 A 4 4 0 0 0 2 2 L 2 16 Z" fill="#89b653" stroke="#4d6f21" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                </motion.g>
              </g>
            </g>

            {/* TỜ MENU */}
            <motion.g 
              initial={false} 
              animate={{ opacity: step === 1 ? 1 : 0, rotate: step === 1 ? -15 : 0, y: step === 1 ? -20 : 10 }} 
              transition={{ duration: 0.5 }}
              transform="translate(160, 210)"
            >
              <rect x="0" y="0" width="70" height="90" fill="#fff" stroke="#ccc" strokeWidth="2" rx="4" />
              <text x="35" y="20" fontSize="14" fill="#333" textAnchor="middle" fontWeight="bold">MENU</text>
              <line x1="10" y1="35" x2="60" y2="35" stroke="#999" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="10" y1="45" x2="50" y2="45" stroke="#999" strokeWidth="2" strokeLinecap="round" />
              <line x1="10" y1="55" x2="55" y2="55" stroke="#999" strokeWidth="2" strokeLinecap="round" />
              <line x1="10" y1="65" x2="40" y2="65" stroke="#999" strokeWidth="2" strokeLinecap="round" />
              <text x="35" y="80" fontSize="30" fill="#222" textAnchor="middle" fontWeight="black">?</text>
            </motion.g>

            {/* ĐIỆN THOẠI */}
            <motion.g 
              initial={false}
              animate={getPhoneTransform()}
              transition={{ duration: 0.6, ease: "easeInOut" }}
            >
              <rect x="0" y="0" width="50" height="90" fill="#222" rx="8" />
              <rect x="3" y="3" width="44" height="84" fill={step >= 4 ? "#fff" : "#4285F4"} rx="5" />
              
              <motion.g animate={{ opacity: step === 2 ? 1 : 0 }}>
                <rect x="0" y="3" width="50" height="20" fill="#fff" />
                <text x="25" y="16" fontSize="8" fill="#333" textAnchor="middle" fontWeight="bold">G Dịch</text>
                <text x="25" y="45" fontSize="10" fill="#fff" textAnchor="middle" fontWeight="bold">Rock soup</text>
                <text x="25" y="58" fontSize="10" fill="#fff" textAnchor="middle" fontWeight="bold">grill bread?</text>
                <circle cx="25" cy="75" r="8" fill="#e14e4e" />
                <path d="M 21 73 L 29 77 M 29 73 L 21 77" stroke="#fff" strokeWidth="2" />
              </motion.g>

              <motion.g animate={{ opacity: step === 4 ? 1 : 0 }}>
                <rect x="5" y="8" width="40" height="10" fill="#eee" rx="3" />
                <text x="25" y="15" fontSize="6" fill="#333" textAnchor="middle">menuscan.vn</text>
                <motion.circle 
                  cx="25" cy="45" r="10" 
                  fill="none" stroke="#ccc" strokeWidth="3" 
                  strokeDasharray="20"
                  animate={step === 4 ? { rotate: 360 } : {}}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
                <text x="25" y="65" fontSize="8" fill="#666" textAnchor="middle">Loading...</text>
              </motion.g>

              {/* Màn hình Scan Menu (Step 5) */}
              <motion.g animate={{ opacity: step === 5 ? 1 : 0 }}>
                {/* 1. Hình ảnh tờ Menu thu nhỏ đang nằm trên màn hình */}
                <rect x="8" y="8" width="34" height="74" fill="#fdfaf5" stroke="#ccc" strokeWidth="1" rx="2" />
                <text x="25" y="18" fontSize="6" fill="#333" textAnchor="middle" fontWeight="bold">MENU</text>
                <line x1="12" y1="24" x2="38" y2="24" stroke="#999" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="12" y1="30" x2="30" y2="30" stroke="#999" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="12" y1="36" x2="35" y2="36" stroke="#999" strokeWidth="1.5" strokeLinecap="round" />
                
                {/* Dòng chữ đang được Highlight (Giả lập đang scan dòng này) */}
                <rect x="10" y="40" width="26" height="6" fill="#58cc02" opacity="0.2" rx="1" />
                <line x1="12" y1="43" x2="33" y2="43" stroke="#333" strokeWidth="1.5" strokeLinecap="round" />
                
                <line x1="12" y1="50" x2="28" y2="50" stroke="#999" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="12" y1="56" x2="35" y2="56" stroke="#999" strokeWidth="1.5" strokeLinecap="round" />

                {/* 2. Khung Scan Laser nhỏ nằm BÊN TRONG màn hình điện thoại */}
                <path d="M 12 20 L 6 20 L 6 26" stroke="#58cc02" strokeWidth="1.5" fill="none" />
                <path d="M 38 20 L 44 20 L 44 26" stroke="#58cc02" strokeWidth="1.5" fill="none" />
                <path d="M 12 58 L 6 58 L 6 52" stroke="#58cc02" strokeWidth="1.5" fill="none" />
                <path d="M 38 58 L 44 58 L 44 52" stroke="#58cc02" strokeWidth="1.5" fill="none" />
                
                {/* Tia sáng rọi xuống */}
                <motion.line 
                  x1="4" y1="20" x2="46" y2="20" 
                  stroke="#58cc02" strokeWidth="1" opacity="0.8" 
                  animate={step === 5 ? { y1: [20, 58, 20], y2: [20, 58, 20] } : {}}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                />

                {/* 3. Kết quả Scan bật lên (Pop-up Phở Bò) */}
                <g transform="translate(5, 64)">
                  <rect x="0" y="0" width="40" height="20" fill="#fff" stroke="#58cc02" strokeWidth="1.5" rx="4" />
                  {/* Icon phở thu nhỏ */}
                  <g transform="translate(10, 10) scale(0.22)">
                    <path d="M -35 0 Q -30 25 0 30 Q 30 25 35 0 Z" fill="#fff" stroke="#e8a44c" strokeWidth="4" />
                    <ellipse cx="0" cy="0" rx="35" ry="10" fill="#e8a44c" />
                    <path d="M -15 0 L -10 12" stroke="#c1432e" strokeWidth="2.5" />
                  </g>
                  {/* Chữ */}
                  <text x="27" y="10" fontSize="5.5" fill="#333" textAnchor="middle" fontWeight="black">PHỞ BÒ</text>
                  <rect x="20" y="13" width="14" height="2.5" fill="#58cc02" rx="1" />
                </g>
              </motion.g>
            </motion.g>

            {/* BÓNG ĐÈN Ý TƯỞNG */}
            <motion.g 
              initial={false}
              animate={{ 
                opacity: step === 3 ? 1 : 0, 
                scale: step === 3 ? 1 : 0.5,
                y: step === 3 ? [0, -5, 0] : 30 
              }} 
              transition={{ duration: 0.5, y: { repeat: Infinity, duration: 1.5, ease: 'easeInOut' } }}
              transform="translate(150, 0)"
            >
              <circle cx="0" cy="-10" r="35" fill="#ffc800" opacity="0.4" filter="blur(8px)" />
              <rect x="-8" y="10" width="16" height="12" fill="#555" rx="2" />
              <line x1="-7" y1="14" x2="7" y2="14" stroke="#333" strokeWidth="1.5" />
              <line x1="-7" y1="18" x2="7" y2="18" stroke="#333" strokeWidth="1.5" />
              <path d="M -16 -6 A 16 16 0 1 1 16 -6 C 16 8 10 10 10 10 L -10 10 C -10 10 -16 8 -16 -6 Z" fill="#ffdf5d" stroke="#d4a822" strokeWidth="2.5" />
              <path d="M -5 10 L -5 0 L 0 -5 L 5 0 L 5 10" stroke="#d4a822" strokeWidth="2" fill="none" />
              <line x1="-22" y1="-22" x2="-32" y2="-32" stroke="#ffc800" strokeWidth="3" strokeLinecap="round" />
              <line x1="0" y1="-28" x2="0" y2="-42" stroke="#ffc800" strokeWidth="3" strokeLinecap="round" />
              <line x1="22" y1="-22" x2="32" y2="-32" stroke="#ffc800" strokeWidth="3" strokeLinecap="round" />
              <text x="-40" y="10" fontSize="16" fill="#333" fontWeight="black" transform="rotate(-15)">Aha!</text>
            </motion.g>
          </motion.g>

        </svg>
      </div>

    </div>
  )
}
