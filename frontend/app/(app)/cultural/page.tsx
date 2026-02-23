'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import api from '@/lib/api';

type CulturalSignal = {
  concept: string;
  explanation: string;
  relevance: string;
};

type CulturalAnalysisResponse = {
  tone_category: string;
  directness_score: number;
  implied_meaning: string;
  cultural_signals: CulturalSignal[];
  suggested_response_tone: string;
  summary: string;
};

type RewriteResponse = {
  original: string;
  rewritten: string;
  changes_made: string[];
  tone_achieved: string;
};

export default function CulturalPage() {
  const [analyzeText, setAnalyzeText] = useState('');
  const [analyzeContext, setAnalyzeContext] = useState('workplace');
  const [analysis, setAnalysis] = useState<CulturalAnalysisResponse | null>(null);

  const [rewriteText, setRewriteText] = useState('');
  const [rewriteContext, setRewriteContext] = useState('workplace email');
  const [targetRegister, setTargetRegister] = useState<'professional' | 'friendly-professional' | 'formal'>('professional');
  const [rewrite, setRewrite] = useState<RewriteResponse | null>(null);

  const [loading, setLoading] = useState(false);

  const analyze = async () => {
    setLoading(true);
    try {
      const response = await api.post<CulturalAnalysisResponse>('/api/v1/cultural/analyze', {
        text: analyzeText,
        context: analyzeContext,
      });
      setAnalysis(response.data);
    } finally {
      setLoading(false);
    }
  };

  const rewriteDraft = async () => {
    setLoading(true);
    try {
      const response = await api.post<RewriteResponse>('/api/v1/cultural/rewrite', {
        text: rewriteText,
        target_register: targetRegister,
        context: rewriteContext,
      });
      setRewrite(response.data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="font-[family-name:var(--font-display)] text-4xl text-slate-900">Cultural Interpreter</h1>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle>Analyze Message</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={analyzeText}
              onChange={(e) => setAnalyzeText(e.target.value)}
              rows={7}
              placeholder="Paste an email/message to analyze..."
            />
            <div className="space-y-1">
              <Label>Context</Label>
              <Input value={analyzeContext} onChange={(e) => setAnalyzeContext(e.target.value)} />
            </div>
            <Button onClick={analyze} disabled={loading || analyzeText.trim().length < 10}>
              Analyze
            </Button>

            {analysis ? (
              <div className="space-y-2 rounded-lg border border-blue-200 bg-white p-3 text-sm">
                <p>
                  <strong>Tone:</strong> {analysis.tone_category} ({analysis.directness_score}/10)
                </p>
                <p>
                  <strong>Implied meaning:</strong> {analysis.implied_meaning}
                </p>
                <p>
                  <strong>Suggested response tone:</strong> {analysis.suggested_response_tone}
                </p>
                <p>
                  <strong>Summary:</strong> {analysis.summary}
                </p>
                <div>
                  <strong>Cultural signals:</strong>
                  <ul className="list-disc pl-5">
                    {analysis.cultural_signals.map((signal) => (
                      <li key={`${signal.concept}-${signal.relevance}`}>
                        <span className="font-medium">{signal.concept}:</span> {signal.relevance}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle>Rewrite Draft</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={rewriteText}
              onChange={(e) => setRewriteText(e.target.value)}
              rows={7}
              placeholder="Write your draft here..."
            />
            <div className="space-y-1">
              <Label>Target Register</Label>
              <Select
                value={targetRegister}
                onValueChange={(value: 'professional' | 'friendly-professional' | 'formal') =>
                  setTargetRegister(value)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select register" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="professional">Professional</SelectItem>
                  <SelectItem value="friendly-professional">Friendly-Professional</SelectItem>
                  <SelectItem value="formal">Formal</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Context</Label>
              <Input value={rewriteContext} onChange={(e) => setRewriteContext(e.target.value)} />
            </div>
            <Button onClick={rewriteDraft} disabled={loading || rewriteText.trim().length < 10}>
              Rewrite
            </Button>

            {rewrite ? (
              <div className="space-y-2 rounded-lg border border-blue-200 bg-white p-3 text-sm">
                <p>
                  <strong>Rewritten:</strong>
                </p>
                <p className="whitespace-pre-wrap">{rewrite.rewritten}</p>
                <p>
                  <strong>Tone achieved:</strong> {rewrite.tone_achieved}
                </p>
                <div>
                  <strong>Changes made:</strong>
                  <ul className="list-disc pl-5">
                    {rewrite.changes_made.map((change) => (
                      <li key={change}>{change}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
