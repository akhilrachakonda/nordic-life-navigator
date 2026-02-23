import Link from 'next/link';

import { Button } from '@/components/ui/button';

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-br from-blue-100 via-slate-50 to-cyan-100">
      <div className="absolute -left-20 top-20 h-64 w-64 rounded-full bg-blue-300/30 blur-3xl" />
      <div className="absolute right-0 top-0 h-80 w-80 rounded-full bg-cyan-300/30 blur-3xl" />

      <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6 py-20">
        <p className="mb-4 inline-flex w-fit rounded-full border border-blue-200 bg-white/90 px-4 py-1 text-xs uppercase tracking-[0.18em] text-blue-700">
          Nordic Life Navigator
        </p>
        <h1 className="max-w-3xl font-[family-name:var(--font-display)] text-5xl leading-tight text-slate-900 md:text-6xl">
          Understand Swedish systems with an AI guide built for real life.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-700">
          Chat about permits, deadlines, financial survival, wellbeing, and cultural communication,
          all in one assistant designed for international students and migrants.
        </p>

        <div className="mt-10 flex flex-wrap gap-4">
          <Button asChild size="lg" className="bg-blue-700 hover:bg-blue-800">
            <Link href="/login">Login</Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="border-blue-300 bg-white/80">
            <Link href="/dashboard">Open Dashboard</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
