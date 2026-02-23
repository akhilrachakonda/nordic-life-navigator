'use client';

import { GoogleAuthProvider, createUserWithEmailAndPassword, signInWithEmailAndPassword, signInWithPopup } from 'firebase/auth';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { auth } from '@/lib/firebase';
import { useAuth } from '@/lib/hooks/useAuth';

export default function LoginPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!loading && user) {
    router.replace('/dashboard');
  }

  const onGoogle = async () => {
    if (!auth) {
      setError('Firebase auth is not initialized.');
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
      router.replace('/dashboard');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Google sign-in failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const onEmail = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (!auth) {
        throw new Error('Firebase auth is not initialized.');
      }

      if (mode === 'login') {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        await createUserWithEmailAndPassword(auth, email, password);
      }
      router.replace('/dashboard');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Authentication failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-100 via-slate-50 to-cyan-100 px-4">
      <Card className="w-full max-w-md border-blue-200 bg-white/90 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-2xl">Welcome Back</CardTitle>
          <CardDescription>Sign in with Google or email to continue.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={onGoogle} className="w-full bg-blue-700 hover:bg-blue-800" disabled={isSubmitting}>
            Continue with Google
          </Button>

          <div className="text-center text-xs text-slate-500">or use email</div>

          <form onSubmit={onEmail} className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>

            {error ? <p className="text-sm text-red-600">{error}</p> : null}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {mode === 'login' ? 'Login with Email' : 'Create Account'}
            </Button>
          </form>

          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={() => setMode((prev) => (prev === 'login' ? 'signup' : 'login'))}
          >
            {mode === 'login' ? 'Need an account? Sign up' : 'Have an account? Login'}
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
