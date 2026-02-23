'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { BSIGauge } from '@/components/financial/BSIGauge';
import { ExpenseChart } from '@/components/financial/ExpenseChart';
import { ForecastLine } from '@/components/financial/ForecastLine';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';

type FinancialSummary = {
  total_expenses_30d: number;
  total_income_monthly: number;
  burn_rate_daily: number;
  runway_days: number;
  category_breakdown: Record<string, number>;
  expense_count_30d: number;
};

type ForecastResponse = {
  runway_days: number;
  burn_rate_daily: number;
  survival_score: number;
  model_version: string;
  forecast_date: string;
  status: string;
  message?: string;
};

type Expense = {
  id: number;
  amount: number;
  category: string;
  expense_date: string;
  description?: string;
  is_recurring: boolean;
};

type ExpenseResponse = {
  expenses: Expense[];
  count: number;
};

const categories = [
  'rent',
  'food',
  'transport',
  'utilities',
  'entertainment',
  'education',
  'healthcare',
  'other',
] as const;

export default function FinancialPage() {
  const queryClient = useQueryClient();

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    amount: '0',
    category: 'food',
    expense_date: new Date().toISOString().slice(0, 10),
    description: '',
  });

  const summaryQuery = useQuery({
    queryKey: ['financial-summary'],
    queryFn: async () => (await api.get<FinancialSummary>('/api/v1/financial/summary')).data,
  });

  const forecastQuery = useQuery({
    queryKey: ['financial-forecast'],
    queryFn: async () => (await api.get<ForecastResponse>('/api/v1/financial/forecast')).data,
  });

  const expensesQuery = useQuery({
    queryKey: ['financial-expenses'],
    queryFn: async () => (await api.get<ExpenseResponse>('/api/v1/financial/expenses')).data,
  });

  const addExpense = useMutation({
    mutationFn: async () => {
      await api.post('/api/v1/financial/expenses', {
        amount: Number(form.amount),
        category: form.category,
        currency: 'SEK',
        expense_date: form.expense_date,
        description: form.description,
        is_recurring: form.category === 'rent',
      });
    },
    onSuccess: () => {
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ['financial-summary'] });
      queryClient.invalidateQueries({ queryKey: ['financial-expenses'] });
      queryClient.invalidateQueries({ queryKey: ['financial-forecast'] });
    },
  });

  const expenseChartData = useMemo(
    () =>
      Object.entries(summaryQuery.data?.category_breakdown ?? {}).map(([category, amount]) => ({
        category,
        amount,
      })),
    [summaryQuery.data?.category_breakdown],
  );

  const bsiValue = useMemo(() => {
    const survival = forecastQuery.data?.survival_score ?? 0;
    return Math.max(0, Math.min(100, 100 - survival));
  }, [forecastQuery.data?.survival_score]);

  const forecastLineData = useMemo(() => {
    const burnRate = forecastQuery.data?.burn_rate_daily ?? 0;
    const startBalance = (summaryQuery.data?.total_income_monthly ?? 0) * 2;

    return Array.from({ length: 30 }).map((_, index) => ({
      day: `D${index + 1}`,
      balance: Math.max(0, startBalance - burnRate * index),
    }));
  }, [forecastQuery.data?.burn_rate_daily, summaryQuery.data?.total_income_monthly]);

  const survival = Math.max(0, Math.min(100, Math.round(forecastQuery.data?.survival_score ?? 0)));

  return (
    <div className="space-y-6">
      <h1 className="font-[family-name:var(--font-display)] text-4xl text-slate-900">Financial</h1>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="expenses">Expenses</TabsTrigger>
          <TabsTrigger value="forecast">Forecast</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle>Budget Stress Index</CardTitle>
              </CardHeader>
              <CardContent>
                <BSIGauge value={bsiValue} />
              </CardContent>
            </Card>

            <Card className="border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle>Category Spend (30d)</CardTitle>
              </CardHeader>
              <CardContent>
                <ExpenseChart data={expenseChartData} />
              </CardContent>
            </Card>
          </div>

          <Card className="border-blue-200 bg-blue-50">
            <CardHeader>
              <CardTitle>Runway</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-semibold text-slate-900">
                {summaryQuery.data?.runway_days ?? 0} days of runway
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="expenses" className="space-y-4">
          <Card className="border-blue-200 bg-blue-50">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Recent Expenses</CardTitle>
              <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger asChild>
                  <Button>Add Expense</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Expense</DialogTitle>
                    <DialogDescription>Add a manual expense entry.</DialogDescription>
                  </DialogHeader>

                  <div className="space-y-3">
                    <div className="space-y-1">
                      <Label htmlFor="amount">Amount (SEK)</Label>
                      <Input
                        id="amount"
                        type="number"
                        min="0"
                        value={form.amount}
                        onChange={(e) => setForm((prev) => ({ ...prev, amount: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-1">
                      <Label htmlFor="category">Category</Label>
                      <Select
                        value={form.category}
                        onValueChange={(value) => setForm((prev) => ({ ...prev, category: value }))}
                      >
                        <SelectTrigger id="category">
                          <SelectValue placeholder="Select category" />
                        </SelectTrigger>
                        <SelectContent>
                          {categories.map((category) => (
                            <SelectItem key={category} value={category}>
                              {category}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <Label htmlFor="expense-date">Date</Label>
                      <Input
                        id="expense-date"
                        type="date"
                        value={form.expense_date}
                        onChange={(e) =>
                          setForm((prev) => ({ ...prev, expense_date: e.target.value }))
                        }
                      />
                    </div>

                    <div className="space-y-1">
                      <Label htmlFor="description">Description</Label>
                      <Input
                        id="description"
                        value={form.description}
                        onChange={(e) =>
                          setForm((prev) => ({ ...prev, description: e.target.value }))
                        }
                      />
                    </div>

                    <Button className="w-full" onClick={() => addExpense.mutate()}>
                      Save Expense
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>

            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Recurring</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(expensesQuery.data?.expenses ?? []).map((expense) => (
                    <TableRow key={expense.id}>
                      <TableCell>{new Date(expense.expense_date).toLocaleDateString()}</TableCell>
                      <TableCell className="capitalize">{expense.category}</TableCell>
                      <TableCell>{expense.amount.toFixed(0)} SEK</TableCell>
                      <TableCell>
                        {expense.is_recurring ? <Badge variant="secondary">Recurring</Badge> : 'No'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="forecast" className="space-y-4">
          <Card className="border-blue-200 bg-blue-50">
            <CardHeader>
              <CardTitle>30-Day Projection</CardTitle>
            </CardHeader>
            <CardContent>
              <ForecastLine data={forecastLineData} />
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle>Burn Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold text-slate-900">
                  Spending ~{(forecastQuery.data?.burn_rate_daily ?? 0).toFixed(2)} SEK/day
                </p>
              </CardContent>
            </Card>

            <Card className="border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle>Survival Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  className="mx-auto grid h-28 w-28 place-items-center rounded-full"
                  style={{
                    background: `conic-gradient(#2563eb ${survival * 3.6}deg, #dbeafe 0deg)`,
                  }}
                >
                  <div className="grid h-20 w-20 place-items-center rounded-full bg-white text-lg font-semibold text-slate-900">
                    {survival}%
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
