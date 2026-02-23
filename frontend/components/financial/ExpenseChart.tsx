'use client';

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type ExpensePoint = {
  category: string;
  amount: number;
};

type ExpenseChartProps = {
  data: ExpensePoint[];
};

export function ExpenseChart({ data }: ExpenseChartProps) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <XAxis dataKey="category" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value: number | string | undefined) => {
              const numericValue = Number(value ?? 0);
              return `${numericValue.toFixed(0)} SEK`;
            }}
          />
          <Bar dataKey="amount" fill="#3b82f6" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
