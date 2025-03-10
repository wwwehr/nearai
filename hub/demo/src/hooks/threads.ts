import { useCallback, useMemo } from 'react';
import { type z } from 'zod';

import { type threadMessageModel, type threadModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { type AppRouterOutputs } from '~/trpc/router';
import { trpc } from '~/trpc/TRPCProvider';

import { useQueryParams } from './url';

export type ThreadSummary = z.infer<typeof threadModel> & {
  agent: {
    name: string;
    namespace: string;
    version: string;
    url: string;
  };
  lastMessageAt: Date | null;
  messageCount: number;
  url: string;
};

export function useThreads() {
  const accountId = useAuthStore((store) => store.auth?.account_id);
  const utils = trpc.useUtils();

  const threadsQuery = trpc.hub.threads.useQuery(undefined, {
    enabled: !!accountId,
  });

  const setThreadData = useCallback(
    (id: string, data: Partial<AppRouterOutputs['hub']['threads'][number]>) => {
      const threads = [...(threadsQuery.data ?? [])].map((thread) => {
        if (thread.id === id) {
          return {
            ...thread,
            ...data,
          };
        }

        return thread;
      });

      utils.hub.threads.setData(undefined, threads);
    },
    [utils, threadsQuery.data],
  );

  const threads = useMemo(() => {
    if (!accountId) return [];
    if (!threadsQuery.data) return;

    const result: ThreadSummary[] = [];

    for (const data of threadsQuery.data) {
      const rootAgentId = data.metadata.agent_ids?.[0];
      if (!rootAgentId) continue;

      const [namespace, name, version, ...otherSegments] =
        rootAgentId.split('/');
      if (!namespace || !name || !version || otherSegments.length > 0) continue;

      const agentUrl = `/agents/${namespace}/${name}/${version}`;
      const threadUrl = `${agentUrl}/run?threadId=${encodeURIComponent(data.id)}`;

      result.push({
        ...data,
        metadata: {
          ...data.metadata,
          topic: data.metadata.topic || name,
        },
        agent: {
          name,
          namespace,
          version,
          url: agentUrl,
        },
        lastMessageAt: new Date(),
        messageCount: 0,
        url: threadUrl,
      });
    }

    return result;
  }, [accountId, threadsQuery.data]);

  return {
    setThreadData,
    threads,
    threadsQuery,
  };
}

export type MessageGroup = {
  isRootThread: boolean;
  threadId: string;
  messages: z.infer<typeof threadMessageModel>[];
};

export function useGroupedThreadMessages(
  messages: z.infer<typeof threadMessageModel>[],
) {
  const { queryParams } = useQueryParams(['threadId']);
  const rootThreadId = queryParams.threadId!;

  const groupedMessages = useMemo(() => {
    const result: MessageGroup[] = [];

    messages.forEach((message) => {
      const latestGroup = result.length > 0 ? result.at(-1) : undefined;

      if (latestGroup?.threadId === message.thread_id) {
        latestGroup.messages.push(message);
        return;
      } else {
        result.push({
          isRootThread:
            message.thread_id === rootThreadId ||
            message.thread_id === '' ||
            !rootThreadId,
          threadId: message.thread_id,
          messages: [message],
        });
      }
    });

    return result;
  }, [messages, rootThreadId]);

  return {
    groupedMessages,
  };
}
