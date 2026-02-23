'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { useMemo, useState } from 'react';

import { ChatInput } from '@/components/chat/ChatInput';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import api from '@/lib/api';
import { useStream } from '@/lib/hooks/useStream';

type Conversation = {
  conversation_id: string;
  title: string;
  updated_at?: string;
};

type ConversationsResponse = {
  conversations: Conversation[];
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
};

export default function ChatPage() {
  const queryClient = useQueryClient();
  const { streamChat, isStreaming, error } = useStream();

  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [messagesByConversation, setMessagesByConversation] = useState<Record<string, ChatMessage[]>>({
    draft: [],
  });

  const { data: conversationsData } = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => {
      const response = await api.get<ConversationsResponse>('/api/v1/bureaucracy/conversations');
      return response.data;
    },
  });

  const activeKey = selectedConversationId ?? 'draft';
  const activeMessages = messagesByConversation[activeKey] ?? [];

  const conversationItems = useMemo(
    () => conversationsData?.conversations ?? [],
    [conversationsData?.conversations],
  );

  const updateActiveMessages = (updater: (current: ChatMessage[]) => ChatMessage[]) => {
    setMessagesByConversation((prev) => {
      const current = prev[activeKey] ?? [];
      return {
        ...prev,
        [activeKey]: updater(current),
      };
    });
  };

  const sendMessage = async (message: string) => {
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
    };

    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
    };

    updateActiveMessages((current) => [...current, userMessage, assistantMessage]);

    await streamChat(
      message,
      selectedConversationId,
      (token) => {
        updateActiveMessages((current) =>
          current.map((entry) =>
            entry.id === assistantMessageId
              ? { ...entry, content: `${entry.content}${token}` }
              : entry,
          ),
        );
      },
      (conversationId) => {
        if (!selectedConversationId) {
          setMessagesByConversation((prev) => {
            const draftMessages = prev.draft ?? [];
            const rest = { ...prev };
            delete rest.draft;
            return {
              ...rest,
              [conversationId]: draftMessages,
            };
          });
          setSelectedConversationId(conversationId);
        }

        queryClient.invalidateQueries({ queryKey: ['conversations'] });
      },
    );
  };

  return (
    <div className="grid gap-4 md:grid-cols-[280px_1fr]">
      <Card className="h-[70vh] overflow-hidden border-blue-200 bg-white/90">
        <div className="flex items-center justify-between border-b border-blue-100 p-3">
          <h2 className="font-semibold">Conversations</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSelectedConversationId(null);
              setMessagesByConversation((prev) => ({ ...prev, draft: [] }));
            }}
          >
            <Plus className="mr-1 h-4 w-4" />
            New Chat
          </Button>
        </div>

        <div className="h-full overflow-y-auto p-2">
          {conversationItems.length === 0 ? (
            <p className="p-2 text-sm text-slate-500">No saved conversations yet.</p>
          ) : null}

          {conversationItems.map((conversation) => {
            const active = selectedConversationId === conversation.conversation_id;
            return (
              <button
                key={conversation.conversation_id}
                className={`mb-2 w-full rounded-lg border px-3 py-2 text-left transition ${
                  active
                    ? 'border-blue-300 bg-blue-50'
                    : 'border-transparent hover:border-blue-100 hover:bg-blue-50/50'
                }`}
                onClick={() => setSelectedConversationId(conversation.conversation_id)}
              >
                <p className="truncate text-sm font-medium text-slate-900">{conversation.title}</p>
                <p className="text-xs text-slate-500">
                  {conversation.updated_at
                    ? new Date(conversation.updated_at).toLocaleString()
                    : 'No timestamp'}
                </p>
              </button>
            );
          })}
        </div>
      </Card>

      <Card className="flex h-[70vh] flex-col gap-3 border-blue-200 bg-white/90 p-3">
        <ChatWindow messages={activeMessages} isStreaming={isStreaming} />
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <ChatInput onSend={sendMessage} disabled={isStreaming} />
      </Card>
    </div>
  );
}
