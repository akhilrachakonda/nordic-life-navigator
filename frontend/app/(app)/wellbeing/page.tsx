'use client';

import { useQuery } from '@tanstack/react-query';

import { WellbeingCard } from '@/components/wellbeing/WellbeingCard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';

type WellbeingSummary = {
  current_risk_level: 'low' | 'medium' | 'high';
  current_risk_score: number;
  signal_count_7d: number;
  top_categories: string[];
  disclaimer: string;
};

type Signal = {
  signal_id: string;
  category: string;
  intensity: string;
  confidence: number;
  trigger_quote: string;
  created_at?: string;
};

type SignalsResponse = {
  signals: Signal[];
  count: number;
  disclaimer: string;
};

export default function WellbeingPage() {
  const summaryQuery = useQuery({
    queryKey: ['wellbeing-summary'],
    queryFn: async () => (await api.get<WellbeingSummary>('/api/v1/wellbeing/summary')).data,
  });

  const signalsQuery = useQuery({
    queryKey: ['wellbeing-signals'],
    queryFn: async () => (await api.get<SignalsResponse>('/api/v1/wellbeing/signals')).data,
  });

  const summary = summaryQuery.data;

  return (
    <div className="space-y-6">
      <h1 className="font-[family-name:var(--font-display)] text-4xl text-slate-900">Wellbeing</h1>

      <WellbeingCard
        level={summary?.current_risk_level ?? 'low'}
        score={summary?.current_risk_score ?? 0}
        signals7d={summary?.signal_count_7d ?? 0}
      />

      <Card className="border-blue-200 bg-blue-50">
        <CardHeader>
          <CardTitle>Recent Signals</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {(signalsQuery.data?.signals ?? []).length === 0 ? (
            <p className="text-sm text-slate-600">No recent wellbeing signals detected.</p>
          ) : null}

          {signalsQuery.data?.signals.map((signal) => (
            <div key={signal.signal_id} className="rounded-lg border border-blue-200 bg-white p-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium capitalize text-slate-900">{signal.category.replace('_', ' ')}</p>
                <p className="text-xs uppercase tracking-wide text-slate-500">{signal.intensity}</p>
                <p className="text-xs text-slate-500">confidence {(signal.confidence * 100).toFixed(0)}%</p>
              </div>
              <p className="mt-1 text-sm text-slate-700">
                &ldquo;{signal.trigger_quote}&rdquo;
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
