'use client';

import { useQuery } from '@tanstack/react-query';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';

type Deadline = {
  deadline_id: string;
  agency: string;
  action: string;
  deadline_date: string | null;
  urgency: 'critical' | 'important' | 'informational';
  status: string;
};

type DeadlinesResponse = {
  deadlines: Deadline[];
  count: number;
};

export default function DeadlinesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['deadlines', 'list'],
    queryFn: async () => {
      const response = await api.get<DeadlinesResponse>('/api/v1/deadlines', {
        params: { status_filter: 'all' },
      });
      return response.data;
    },
  });

  return (
    <div className="space-y-6">
      <h1 className="font-[family-name:var(--font-display)] text-4xl text-slate-900">Deadlines</h1>

      <Card className="border-blue-200 bg-blue-50">
        <CardHeader>
          <CardTitle>Tracked Deadlines</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? <p className="text-sm text-slate-500">Loading deadlines...</p> : null}
          {!isLoading && (data?.deadlines.length ?? 0) === 0 ? (
            <p className="text-sm text-slate-600">No deadlines yet. Ask the chat to extract tasks.</p>
          ) : null}

          {data?.deadlines.map((deadline) => (
            <div key={deadline.deadline_id} className="rounded-xl border border-blue-200 bg-white p-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium text-slate-900">{deadline.action}</p>
                <Badge variant="secondary" className="capitalize">
                  {deadline.urgency}
                </Badge>
                <Badge variant="outline" className="capitalize">
                  {deadline.status}
                </Badge>
              </div>
              <p className="text-sm text-slate-600">{deadline.agency}</p>
              <p className="text-xs text-slate-500">
                Due:{' '}
                {deadline.deadline_date
                  ? new Date(deadline.deadline_date).toLocaleDateString()
                  : 'No exact date'}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
