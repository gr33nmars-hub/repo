import { useId } from 'react'

interface SlotSymbolProps {
  value: string
}

const labels: Record<string, { label: string; art: 'cherry' | 'lemon' | 'bell' | 'diamond' | 'seven' }> = {
  '1f352': { label: 'Вишни', art: 'cherry' },
  '1f34b': { label: 'Лимон', art: 'lemon' },
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
        <linearGradient id={`${gradientId}-lemon`} x1="0" y1="0" x2=".3" y2="1">
          <stop stopColor="#fff9b5" />
          <stop offset=".55" stopColor="#f5d744" />
          <stop offset="1" stopColor="#dca42b" />
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

      {art === 'lemon' && <g filter={`url(#${gradientId}-shadow)`}>
        <path d="M8 45c5-2 8-6 10-12 5-11 16-16 28-16 15 0 25 9 28 20 1 4 5 7 9 8-5 2-8 6-9 11-5 11-15 16-29 16-12 0-22-6-27-16-2-5-5-9-10-11Z" fill={`url(#${gradientId}-lemon)`} stroke="#a67b20" strokeWidth="2.5" strokeLinejoin="round" />
        <path d="M23 37c5-9 13-13 24-13" fill="none" stroke="#fffbd0" strokeWidth="4" strokeLinecap="round" opacity=".85" />
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
