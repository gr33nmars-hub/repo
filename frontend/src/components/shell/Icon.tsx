import type { SVGProps } from 'react'

export type ShellIconName = 'home' | 'blackjack' | 'slots' | 'roulette' | 'history' | 'arrow' | 'coin' | 'wifi' | 'retry'

const sharedProps: SVGProps<SVGSVGElement> = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.65,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
}

export function Icon({ name, ...props }: { name: ShellIconName } & SVGProps<SVGSVGElement>) {
  return (
    <svg {...sharedProps} {...props}>
      {name === 'home' && <><path d="m3.5 10 8.5-7 8.5 7" /><path d="M5.5 9v11h13V9M9.5 20v-6h5v6" /></>}
      {name === 'blackjack' && <><path d="M12 3.5C10 6.3 4 9.8 4 14.2a4.6 4.6 0 0 0 4.7 4.8c1.4 0 2.5-.6 3.3-1.7.8 1.1 1.9 1.7 3.3 1.7a4.6 4.6 0 0 0 4.7-4.8c0-4.4-6-7.9-8-10.7Z" /><path d="M12 17.3 9.7 21m2.3-3.7 2.3 3.7" /></>}
      {name === 'slots' && <><rect x="3.5" y="4.5" width="17" height="15" rx="2.5" /><path d="M9 4.5v15M15 4.5v15M6.2 10h.1M12 14h.1M17.8 9h.1" /></>}
      {name === 'roulette' && <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="2.1" /><path d="M12 3v6.9m6.4-4.2-4.9 4.9m7.5 1.4h-6.9m4.3 6.4-4.9-4.9m-1.5 7.5v-6.9m-6.3 4.3 4.9-4.9m-7.5-1.5h6.9m-4.3-6.3 4.9 4.9" /></>}
      {name === 'history' && <><path d="M4.5 8.5V4.8m0 0h3.7m-3.7 0 2.6 2.6A8.5 8.5 0 1 1 3.8 13" /><path d="M12 7.5V12l3 2" /></>}
      {name === 'arrow' && <><path d="M5 12h13m-5-5 5 5-5 5" /></>}
      {name === 'coin' && <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5.8" /><path d="M12 8.5v7m2.2-5.2c-.4-.7-1.1-1-2.2-1-1.2 0-2 .5-2 1.3 0 2 4.2.8 4.2 2.8 0 .9-.8 1.5-2.2 1.5-1.1 0-1.9-.4-2.3-1.1" /></>}
      {name === 'wifi' && <><path d="M3 9a14 14 0 0 1 18 0M6 12a9.5 9.5 0 0 1 12 0m-9 3a5 5 0 0 1 6 0m-3 4h.01" /></>}
      {name === 'retry' && <><path d="M20 7v5h-5M4.5 16a8 8 0 0 0 13.6 2.2L20 16m-.5-8A8 8 0 0 0 5.9 5.8L4 8" /></>}
    </svg>
  )
}
