'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';

type DeadlineItem = {
  deadline_id: string;
  agency: string;
  action: string;
  deadline_date: string | null;
  urgency: 'critical' | 'important' | 'informational';
};

type DeadlinesResponse = {
  deadlines: DeadlineItem[];
  count: number;
};

type FinancialSummary = {
  burn_rate_daily: number;
};

type WellbeingSummary = {
  current_risk_level: 'low' | 'medium' | 'high';
};

function riskColor(level: WellbeingSummary['current_risk_level']) {
  if (level === 'high') {
    return 'text-red-600';
  }
  if (level === 'medium') {
    return 'text-amber-600';
  }
  return 'text-emerald-600';
}

export default function DashboardPage() {
  const { data: deadlinesData } = useQuery({
    queryKey: ['deadlines', 'active'],
    queryFn: async () => {
      const response = await api.get<DeadlinesResponse>('/api/v1/deadlines', {
        params: { status_filter: 'active' },
      });
      return response.data;
    },
  });

  const { data: financialData } = useQuery({
    queryKey: ['financial-summary'],
    queryFn: async () => {
      const response = await api.get<FinancialSummary>('/api/v1/financial/summary');
      return response.data;
    },
  });

  const { data: wellbeingData } = useQuery({
    queryKey: ['wellbeing-summary'],
    queryFn: async () => {
      const response = await api.get<WellbeingSummary>('/api/v1/wellbeing/summary');
      return response.data;
    },
  });

  const nextDeadline = [...(deadlinesData?.deadlines ?? [])]
    .filter((d) => d.deadline_date)
    .sort((a, b) => new Date(a.deadline_date ?? '').getTime() - new Date(b.deadline_date ?? '').getTime())[0];

  return (
    <div className="space-y-6">
      <h1 className="font-[family-name:var(--font-display)] text-4xl text-slate-900">Dashboard</h1>
      <p className="text-slate-600">A quick snapshot of deadlines, finances, and wellbeing.</p>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle>Next Deadline</CardTitle>
          </CardHeader>
          <CardContent>
            {nextDeadline ? (
              <div className="space-y-2">
                <p className="text-lg font-semibold text-slate-900">{nextDeadline.action}</p>
                <p className="text-sm text-slate-600">{nextDeadline.agency}</p>
                <p className="text-sm text-slate-700">
                  Due: {new Date(nextDeadline.deadline_date ?? '').toLocaleDateString()}
                </p>
                <span className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-medium capitalize text-blue-700">
                  {nextDeadline.urgency}
                </span>
              </div>
            ) : (
              <p className="text-sm text-slate-600">No active deadlines detected yet.</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle>Burn Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-slate-900">
              {(financialData?.burn_rate_daily ?? 0).toFixed(2)} SEK/day
            </p>
            <p className="text-sm text-slate-600">Based on your 30-day spending pattern.</p>
          </CardContent>
        </Card>

        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle>Wellbeing</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-semibold capitalize ${riskColor(wellbeingData?.current_risk_level ?? 'low')}`}>
              {wellbeingData?.current_risk_level ?? 'low'}
            </p>
            <p className="text-sm text-slate-600">Current risk level from recent check-ins.</p>
          </CardContent>
        </Card>

        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle>Quick Chat</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-slate-600">Ask for step-by-step guidance instantly.</p>
            <Button asChild className="bg-blue-700 hover:bg-blue-800">
              <Link href="/chat">Open Chat</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
