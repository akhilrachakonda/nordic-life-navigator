'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

type WellbeingCardProps = {
  level: string;
  score: number;
  signals7d: number;
};

function levelColor(level: string) {
  if (level === 'high') {
    return 'text-red-600';
  }
  if (level === 'medium') {
    return 'text-amber-600';
  }
  return 'text-emerald-600';
}

export function WellbeingCard({ level, score, signals7d }: WellbeingCardProps) {
  return (
    <Card className="border-blue-200 bg-blue-50">
      <CardHeader>
        <CardTitle>Wellbeing Snapshot</CardTitle>
        <CardDescription>Non-medical wellbeing indicators from recent chats.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className={`text-2xl font-semibold capitalize ${levelColor(level)}`}>{level} risk</p>
        <p className="text-sm text-slate-700">Risk score: {score}/100</p>
        <p className="text-sm text-slate-700">Signals in last 7 days: {signals7d}</p>
        <div className="rounded-lg border border-blue-200 bg-white p-3 text-xs leading-relaxed text-slate-600">
          If you are in crisis, call <strong>112</strong> or contact <strong>Mind 90101</strong>.
          <div className="mt-2">
            <a className="text-blue-700 underline" href="https://mind.se/hitta-hjalp/sjalvmordslinjen/" target="_blank" rel="noreferrer">
              Mind support resources
            </a>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
