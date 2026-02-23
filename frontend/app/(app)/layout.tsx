'use client';

import { Menu } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

import AuthGuard from '@/components/auth/AuthGuard';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { auth } from '@/lib/firebase';

const navItems = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/chat', label: 'Chat' },
  { href: '/deadlines', label: 'Deadlines' },
  { href: '/financial', label: 'Financial' },
  { href: '/cultural', label: 'Cultural' },
  { href: '/wellbeing', label: 'Wellbeing' },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const NavLinks = () => (
    <nav className="space-y-2">
      {navItems.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`block rounded-lg px-3 py-2 text-sm font-medium transition ${
              active ? 'bg-blue-600 text-white' : 'text-slate-700 hover:bg-blue-100'
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-slate-50 to-cyan-50">
        <header className="border-b border-blue-100 bg-white/90 backdrop-blur md:hidden">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
            <p className="font-[family-name:var(--font-display)] text-xl text-slate-900">Nordic</p>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon">
                  <Menu className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-72">
                <SheetHeader>
                  <SheetTitle>Navigation</SheetTitle>
                  <SheetDescription>Move between modules.</SheetDescription>
                </SheetHeader>
                <div className="mt-6">
                  <NavLinks />
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </header>

        <div className="mx-auto grid max-w-7xl md:grid-cols-[240px_1fr]">
          <aside className="hidden min-h-screen border-r border-blue-100 bg-white/80 p-4 md:block">
            <div className="mb-6">
              <h2 className="font-[family-name:var(--font-display)] text-2xl text-slate-900">Nordic</h2>
              <p className="text-xs text-slate-500">Life Navigator</p>
            </div>
            <NavLinks />
            <Button
              variant="ghost"
              className="mt-6 w-full justify-start"
              onClick={async () => {
                await auth?.signOut();
                router.replace('/login');
              }}
            >
              Sign out
            </Button>
          </aside>

          <main className="p-4 md:p-8">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
