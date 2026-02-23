'use client';

import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from 'recharts';

type BSIGaugeProps = {
  value: number;
};

function gaugeColor(value: number) {
  if (value > 70) {
    return '#dc2626';
  }
  if (value >= 40) {
    return '#eab308';
  }
  return '#16a34a';
}

export function BSIGauge({ value }: BSIGaugeProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  const data = [{ name: 'bsi', value: clamped, fill: gaugeColor(clamped) }];

  return (
    <div className="relative h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="90%"
          barSize={18}
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="value" background cornerRadius={10} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-xs uppercase tracking-widest text-slate-500">BSI</p>
        <p className="text-4xl font-semibold text-slate-900">{clamped}</p>
      </div>
    </div>
  );
}
