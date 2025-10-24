import type { Metadata } from 'next'
import { Inter, JetBrains_Mono, Share_Tech_Mono } from 'next/font/google'
import '../styles/globals.css'
import { GlobalAIProvider } from '@/components/global/GlobalAIProvider'
import { ThemeProvider } from '@/components/global/ThemeProvider'

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-inter',
})

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ['latin'],
  variable: '--font-jetbrains-mono',
})

const shareTechMono = Share_Tech_Mono({ 
  subsets: ['latin'],
  weight: '400',
  variable: '--font-share-tech-mono',
})

export const metadata: Metadata = {
  title: 'Stanley - Montreal Canadiens Analytics Assistant',
  description: 'Military-grade hockey analytics interface powered by AI',
  keywords: ['hockey', 'analytics', 'Montreal Canadiens', 'AI', 'Stanley'],
  authors: [{ name: 'HeartBeat Engine Team' }],
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} ${shareTechMono.variable}`}>
      <body className="font-sans antialiased bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-white">
        <ThemeProvider>
          <GlobalAIProvider>
            {children}
          </GlobalAIProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
