interface SlotSymbolProps {
  value: string
}

const symbols: Record<string, { label: string; art: 'cherry' | 'lemon' | 'bell' | 'diamond' | 'seven' }> = {
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
  const symbol = symbols[symbolKey(value)]
  const label = symbol?.label ?? 'Неизвестный символ'

  return (
    <svg className={`slot-symbol slot-symbol--${symbol?.art ?? 'unknown'}`} viewBox="0 0 72 72" role="img" aria-label={label}>
      {symbol?.art === 'cherry' && <><path d="M34 34C34 22 29 14 21 9m18 25C39 21 46 15 54 11" /><path d="M44 13c5-9 16-8 18-7-2 9-8 14-18 7Z" /><circle cx="26" cy="46" r="12" /><circle cx="48" cy="47" r="12" /></>}
      {symbol?.art === 'lemon' && <><path d="M14 37c5-12 14-20 25-20 12 0 21 9 20 20-1 12-11 22-25 22-12 0-23-9-20-22Z" /><path d="M39 18c4-9 13-11 20-8-3 7-10 11-20 8Zm-16 14c7 8 20 14 32 14" /></>}
      {symbol?.art === 'bell' && <><path d="M19 49h34c-5-5-7-11-7-21 0-7-4-12-10-12s-10 5-10 12c0 10-2 16-7 21Z" /><path d="M31 55a5 5 0 0 0 10 0M36 11v5" /></>}
      {symbol?.art === 'diamond' && <><path d="m36 10 23 19-23 34-23-34L36 10Z" /><path d="m13 29 46 0M27 11l-6 18 15 34 15-34-6-18" /></>}
      {symbol?.art === 'seven' && <><path d="M19 17h35L31 59" /><path d="M19 25v-8m35 8v-8" /></>}
      {!symbol && <><path d="M17 17h38v38H17z" /><path d="m25 25 22 22m0-22L25 47" /></>}
    </svg>
  )
}
