'use client';

import ReactMarkdown from 'react-markdown';

import { Badge } from '@/components/ui/badge';

type MessageBubbleProps = {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
};

export function MessageBubble({ role, content, sources = [] }: MessageBubbleProps) {
  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm md:max-w-[75%] ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'border border-slate-200 bg-white text-slate-800'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{content}</p>
        ) : (
          <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-2">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}

        {!isUser && sources.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {sources.map((source) => (
              <Badge key={source} variant="secondary" className="bg-slate-100 text-xs">
                {source}
              </Badge>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
