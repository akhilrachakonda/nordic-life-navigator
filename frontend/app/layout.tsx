import type { Metadata } from 'next';
import { Playfair_Display, Space_Grotesk } from 'next/font/google';

import { AppProviders } from '@/components/providers/AppProviders';

import './globals.css';

const sans = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-sans',
});

const display = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-display',
});

export const metadata: Metadata = {
  title: 'Nordic Life Navigator',
  description: 'AI support for navigating life in Sweden',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${display.variable} min-h-screen bg-slate-50 text-slate-900 antialiased`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
