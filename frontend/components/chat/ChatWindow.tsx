'use client';

import { useEffect, useRef } from 'react';

import { MessageBubble } from '@/components/chat/MessageBubble';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
};

type ChatWindowProps = {
  messages: ChatMessage[];
  isStreaming: boolean;
};

export function ChatWindow({ messages, isStreaming }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  return (
    <div className="flex-1 space-y-4 overflow-y-auto rounded-xl border border-blue-100 bg-blue-50/50 p-4">
      {messages.length === 0 ? (
        <div className="flex h-full min-h-[240px] items-center justify-center text-sm text-slate-500">
          Ask your first question about Swedish bureaucracy.
        </div>
      ) : null}

      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          role={message.role}
          content={message.content}
          sources={message.sources}
        />
      ))}

      {isStreaming ? (
        <div className="flex items-center text-sm text-slate-500">
          <span className="mr-2">Streaming</span>
          <span className="inline-flex h-4 w-4 animate-pulse rounded-full bg-blue-500" />
        </div>
      ) : null}

      <div ref={bottomRef} />
    </div>
  );
}
