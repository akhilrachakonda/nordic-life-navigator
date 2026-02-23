'use client';

import { useCallback, useState } from 'react';

import { auth } from '@/lib/firebase';

export function useStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const streamChat = useCallback(
    async (
      message: string,
      conversationId: string | null,
      onToken: (token: string) => void,
      onDone: (conversationId: string) => void,
    ) => {
      setIsStreaming(true);
      setError(null);

      const user = auth?.currentUser;
      if (!user) {
        setError('Not authenticated');
        setIsStreaming(false);
        return;
      }

      try {
        const token = await user.getIdToken();
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;

        const response = await fetch(`${apiUrl}/api/v1/bureaucracy/chat`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message, conversation_id: conversationId }),
        });

        if (!response.ok || !response.body) {
          setError(`Chat request failed (${response.status})`);
          setIsStreaming(false);
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let activeConvId = conversationId;

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) {
              continue;
            }

            try {
              const event = JSON.parse(line.slice(6)) as {
                conversation_id?: string;
                token?: string;
                done?: boolean;
                error?: boolean;
                error_message?: string;
              };

              if (event.conversation_id) {
                activeConvId = event.conversation_id;
              }
              if (event.token) {
                onToken(event.token);
              }
              if (event.done) {
                if (activeConvId) {
                  onDone(activeConvId);
                }
                setIsStreaming(false);
                return;
              }
              if (event.error) {
                setError(event.error_message ?? 'Streaming failed');
                setIsStreaming(false);
                return;
              }
            } catch {
              // Ignore malformed SSE lines.
            }
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Streaming failed');
      }

      setIsStreaming(false);
    },
    [],
  );

  return { streamChat, isStreaming, error };
}
