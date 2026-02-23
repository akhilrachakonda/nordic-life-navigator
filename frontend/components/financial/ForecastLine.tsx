'use client';

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type ForecastPoint = {
  day: string;
  balance: number;
};

type ForecastLineProps = {
  data: ForecastPoint[];
};

export function ForecastLine({ data }: ForecastLineProps) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#dbeafe" />
          <XAxis dataKey="day" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value: number | string | undefined) => {
              const numericValue = Number(value ?? 0);
              return `${numericValue.toFixed(0)} SEK`;
            }}
          />
          <Line type="monotone" dataKey="balance" stroke="#0ea5e9" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
