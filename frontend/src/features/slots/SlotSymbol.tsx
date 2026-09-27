import { useId } from 'react'

interface SlotSymbolProps {
  value: string
}

const labels: Record<string, { label: string; art: 'cherry' | 'banana' | 'bell' | 'diamond' | 'seven' }> = {
  '1f352': { label: 'Вишни', art: 'cherry' },
  // 🍋 is the stable game symbol; the machine's artwork represents it as a banana.
  '1f34b': { label: 'Банан', art: 'banana' },
  '1f514': { label: 'Колокол', art: 'bell' },
  '1f48e': { label: 'Бриллиант', art: 'diamond' },
  '37-fe0f-20e3': { label: 'Семёрка', art: 'seven' },
}

function symbolKey(value: string) {
  return Array.from(value, (character) => (character.codePointAt(0) ?? 0).toString(16)).join('-')
}

export function SlotSymbol({ value }: SlotSymbolProps) {
  const gradientId = useId().replaceAll(':', '')
  const symbol = labels[symbolKey(value)]
  const art = symbol?.art

  return (
    <svg className={`slot-symbol slot-symbol--${art ?? 'unknown'}`} viewBox="0 0 88 88" role="img" aria-label={symbol?.label ?? 'Неизвестный символ'}>
      <defs>
        <linearGradient id={`${gradientId}-red`} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#ff8680" />
          <stop offset=".4" stopColor="#d63c35" />
          <stop offset="1" stopColor="#8e1820" />
        </linearGradient>
        <linearGradient id={`${gradientId}-gold`} x1="0" y1="0" x2=".8" y2="1">
          <stop stopColor="#fff5ac" />
          <stop offset=".42" stopColor="#f2c848" />
          <stop offset="1" stopColor="#bd741e" />
        </linearGradient>
        <linearGradient id={`${gradientId}-bell`} x1=".15" y1="0" x2=".85" y2="1">
          <stop stopColor="#fff1a0" />
          <stop offset=".35" stopColor="#e2a938" />
          <stop offset=".72" stopColor="#b76b20" />
          <stop offset="1" stopColor="#f5cf63" />
        </linearGradient>
        <linearGradient id={`${gradientId}-gem`} x1=".15" y1="0" x2=".8" y2="1">
          <stop stopColor="#c9ffff" />
          <stop offset=".45" stopColor="#55c7bf" />
          <stop offset="1" stopColor="#14727b" />
        </linearGradient>
        <linearGradient id={`${gradientId}-leaf`} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#afbd55" />
          <stop offset="1" stopColor="#3e6738" />
        </linearGradient>
        <filter id={`${gradientId}-shadow`} x="-.3" y="-.3" width="1.6" height="1.7" colorInterpolationFilters="sRGB">
          <feDropShadow dx="0" dy="3" stdDeviation="2" floodColor="#342511" floodOpacity=".28" />
        </filter>
      </defs>

      {art === 'cherry' && <g filter={`url(#${gradientId}-shadow)`} stroke="#652322" strokeLinejoin="round">
        <path d="M42 46C43 31 35 20 26 13M43 45C46 29 55 19 66 13" fill="none" stroke="#49623b" strokeWidth="4" strokeLinecap="round" />
        <path d="M48 22C52 10 67 8 75 12c-2 13-13 20-27 10Z" fill={`url(#${gradientId}-leaf)`} stroke="#43502d" strokeWidth="2" />
        <path d="m51 22 17-7" fill="none" stroke="#d4d283" strokeWidth="1.5" />
        <path d="M41 43c-11-7-25-1-27 12-2 11 7 22 19 21 12 0 19-12 14-22-1-4-3-8-6-11Z" fill={`url(#${gradientId}-red)`} strokeWidth="2.5" />
        <path d="M61 43c-11-7-24-1-26 12-2 11 7 22 19 21 12 0 19-12 14-22-1-4-3-8-7-11Z" fill={`url(#${gradientId}-red)`} strokeWidth="2.5" />
        <ellipse cx="25" cy="53" rx="3" ry="6" transform="rotate(28 25 53)" fill="#ffe4ca" stroke="none" opacity=".78" />
        <ellipse cx="46" cy="53" rx="3" ry="6" transform="rotate(28 46 53)" fill="#ffe4ca" stroke="none" opacity=".78" />
      </g>}

      {art === 'banana' && <g filter={`url(#${gradientId}-shadow)`} stroke="#89601a" strokeLinejoin="round">
        <path d="M12 58C18 25 44 8 72 14c-3 19-15 34-31 42 16-4 29-17 37-32-3 28-24 48-57 53-10-2-14-9-9-19Z" fill={`url(#${gradientId}-gold)`} strokeWidth="2.5" />
        <path d="M17 57C26 32 44 19 64 18" fill="none" stroke="#fff1a4" strokeWidth="5" strokeLinecap="round" opacity=".8" />
        <path d="m12 58-8-3 3-8 9 2m62-25 3-9 8 2-2 10" fill="#76502b" stroke="#614221" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M19 68c19-3 35-14 47-29" fill="none" stroke="#c27c1c" strokeWidth="2" opacity=".65" />
      </g>}

      {art === 'bell' && <g filter={`url(#${gradientId}-shadow)`} stroke="#80511e" strokeLinejoin="round">
        <path d="M25 57c5-6 7-14 7-26 0-10 5-17 12-17s12 7 12 17c0 12 2 20 7 26l6 6H19l6-6Z" fill={`url(#${gradientId}-bell)`} strokeWidth="2.5" />
        <path d="M31 34c1-8 4-12 9-14" fill="none" stroke="#fff3b0" strokeWidth="3" strokeLinecap="round" opacity=".8" />
        <path d="M20 60h48v6H20z" fill="#b36a20" strokeWidth="2" />
        <path d="M37 68a7 7 0 0 0 14 0" fill="#d39228" strokeWidth="2.5" />
        <path d="M44 10V7" fill="none" stroke="#80511e" strokeWidth="4" strokeLinecap="round" />
      </g>}

      {art === 'diamond' && <g filter={`url(#${gradientId}-shadow)`} stroke="#236b70" strokeLinejoin="round">
        <path d="m13 31 12-15h38l12 15-31 43L13 31Z" fill={`url(#${gradientId}-gem)`} strokeWidth="3" />
        <path d="M13 31h62M25 16l8 15 11 43 11-43 8-15M33 31h22" fill="none" stroke="#e4ffec" strokeWidth="2" opacity=".82" />
        <path d="M13 31h20l11 43L13 31Zm42 0h20L44 74l11-43Z" fill="#eefef0" opacity=".22" stroke="none" />
      </g>}

      {art === 'seven' && <g filter={`url(#${gradientId}-shadow)`}>
        <text x="46" y="70" textAnchor="middle" fontFamily="Arial Black, Impact, sans-serif" fontSize="70" fontWeight="900" fontStyle="italic" fill={`url(#${gradientId}-red)`} stroke="#811f21" strokeWidth="2" paintOrder="stroke">7</text>
        <path d="M23 25h31" stroke="#ffd3a1" strokeWidth="3" strokeLinecap="round" opacity=".8" />
      </g>}

      {!art && <g fill="#777363" stroke="#49483e" strokeWidth="3"><circle cx="44" cy="44" r="30" /><path d="m32 32 24 24m0-24L32 56" /></g>}
    </svg>
  )
}
