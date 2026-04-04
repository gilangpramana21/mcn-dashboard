import type { Metadata } from 'next'
import './globals.css'
import { Providers } from '@/components/Providers'

export const metadata: Metadata = {
  title: 'Influencer Dashboard',
  description: 'TikTok Influencer Marketing Agent Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className="dark">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
