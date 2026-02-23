'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

type ChatInputProps = {
  disabled?: boolean;
  onSend: (message: string) => Promise<void>;
};

export function ChatInput({ disabled = false, onSend }: ChatInputProps) {
  const [value, setValue] = useState('');

  const handleSubmit = async () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }

    setValue('');
    await onSend(trimmed);
  };

  return (
    <div className="space-y-2 border-t border-blue-100 pt-3">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        rows={3}
        placeholder="Ask about permits, Skatteverket, CSN, or anything else..."
        disabled={disabled}
        onKeyDown={async (e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            await handleSubmit();
          }
        }}
      />
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">Enter to send, Shift+Enter for newline</p>
        <Button onClick={handleSubmit} disabled={disabled || value.trim().length === 0}>
          Send
        </Button>
      </div>
    </div>
  );
}
