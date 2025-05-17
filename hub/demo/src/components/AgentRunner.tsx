'use client';

import {
  Badge,
  BreakpointDisplay,
  Button,
  Card,
  CardList,
  Flex,
  Form,
  handleClientError,
  InputTextarea,
  openToast,
  PlaceholderSection,
  PlaceholderStack,
  Text,
  Tooltip,
} from '@nearai/ui';
import { formatBytes } from '@nearai/ui/utils';
import {
  ArrowRight,
  CodeBlock,
  Eye,
  Folder,
  Info,
  List,
} from '@phosphor-icons/react';
import { Paperclip, X } from '@phosphor-icons/react/dist/ssr';
import { useMutation } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import {
  type KeyboardEventHandler,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { FileRejection } from 'react-dropzone';
import { useDropzone } from 'react-dropzone';
import { type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import { AgentPermissionsModal } from '@/components/AgentPermissionsModal';
import { AgentWelcome } from '@/components/AgentWelcome';
import { EntryEnvironmentVariables } from '@/components/EntryEnvironmentVariables';
import { IframeWithBlob } from '@/components/lib/IframeWithBlob';
import { Sidebar } from '@/components/lib/Sidebar';
import { SignInPrompt } from '@/components/SignInPrompt';
import { ThreadMessages } from '@/components/threads/ThreadMessages';
import { ThreadsSidebar } from '@/components/threads/ThreadsSidebar';
import { useAgentRequestsWithIframe } from '@/hooks/agent-iframe-requests';
import { useConsumerModeEnabled } from '@/hooks/consumer';
import { useCurrentEntry, useEntryEnvironmentVariables } from '@/hooks/entries';
import { useQueryParams } from '@/hooks/url';
import { rawFileUrlForEntry, sourceUrlForEntry } from '@/lib/entries';
import { threadFileModel } from '@/lib/models';
import {
  apiErrorModel,
  type chatWithAgentModel,
  type threadMessageModel,
} from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { useThreadsStore } from '@/stores/threads';
import { trpc } from '@/trpc/TRPCProvider';
import { WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS } from '@/utils/wallet';

import s from './AgentRunner.module.scss';
import { ThreadFileModal } from './threads/ThreadFileModal';
import { ThreadThinking } from './threads/ThreadThinking';

import { v4 as uuidv4 } from 'uuid';
import { SecretVaultWrapper } from 'secretvaults';

type Props = {
  namespace: string;
  name: string;
  version: string;
  showLoadingPlaceholder?: boolean;
};

type RunView = 'conversation' | 'output' | undefined;

type FormSchema = Pick<z.infer<typeof chatWithAgentModel>, 'new_message'>;

interface nilDbResult {
  status: number;
  data: {
    created: string[];
    errors: any[];
  };
  node: {
    url: string;
    did: string;
  };
  schemaId: string;
}

interface nilDbEncoded {
  _id: string;
  hosts: string[];
}

function nilDbEncode(sourceArray: nilDbResult[]): nilDbEncoded {
  const id = sourceArray[0].data.created[0] as string;
  const hosts = sourceArray.map((item) => item.node.did);

  return {
    _id: id,
    hosts: hosts,
  };
}

export type AgentChatMutationInput = FormSchema &
  Partial<z.infer<typeof chatWithAgentModel>>;

export const AgentRunner = ({
  namespace,
  name,
  version,
  showLoadingPlaceholder,
}: Props) => {
  const { consumerModeEnabled, embedded } = useConsumerModeEnabled();
  const { currentEntry, currentEntryId: agentId } = useCurrentEntry('agent', {
    overrides: {
      namespace,
      name,
      version,
    },
  });

  const auth = useAuthStore((store) => store.auth);
  const { queryParams, updateQueryPath } = useQueryParams([
    'showLogs',
    'threadId',
    'theme',
    'view',
    'initialUserMessage',
    'mockedAitpMessages',
    ...WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS,
  ]);
  const entryEnvironmentVariables = useEntryEnvironmentVariables(
    currentEntry,
    Object.keys(queryParams),
  );
  const utils = trpc.useUtils();
  const threadId = queryParams.threadId ?? '';
  const showLogs = queryParams.showLogs === 'true';

  const form = useForm<FormSchema>();

  const [htmlOutput, setHtmlOutput] = useState('');
  const [streamingText, setStreamingText] = useState<string>('');
  const [streamingTextLatestChunk, setStreamingTextLatestChunk] =
    useState<string>('');
  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  const [threadsOpenForSmallScreens, setThreadsOpenForSmallScreens] =
    useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);
  const [attachments, setAttachments] = useState<
    z.infer<typeof threadFileModel>[]
  >([]);
  const [isUploadingAttachments, setIsUploadingAttachments] = useState(false);

  const clearOptimisticMessages = useThreadsStore(
    (store) => store.clearOptimisticMessages,
  );
  const addOptimisticMessages = useThreadsStore(
    (store) => store.addOptimisticMessages,
  );
  const optimisticMessages = useThreadsStore(
    (store) => store.optimisticMessages,
  );
  const initialUserMessageSent = useRef(false);
  const chatMutationThreadId = useRef('');
  const chatMutationStartedAt = useRef<Date | null>(null);
  const setThread = useThreadsStore((store) => store.setThread);
  const threadsById = useThreadsStore((store) => store.threadsById);
  const setAddMessage = useThreadsStore((store) => store.setAddMessage);
  const setOpenedFileId = useThreadsStore((store) => store.setOpenedFileId);
  const thread = threadsById[chatMutationThreadId.current || threadId];
  const [stream, setStream] = useState<EventSource | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const _chatMutation = trpc.hub.chatWithAgent.useMutation();
  const chatMutation = useMutation({
    mutationFn: async (data: AgentChatMutationInput) => {
      try {
        chatMutationStartedAt.current = new Date();

        const input = {
          thread_id: threadId || undefined,
          agent_id: agentId,
          agent_env_vars: entryEnvironmentVariables.metadataVariablesByKey,
          user_env_vars: entryEnvironmentVariables.urlVariablesByKey,
          attachments: attachments.map((attachment) => ({
            file_id: attachment.id,
          })),
          ...data,
        };

        form.setValue('new_message', '');
        setAttachments([]);

        addOptimisticMessages(threadId, [input]);
        const response = await _chatMutation.mutateAsync(input);
        setThread({
          ...response.thread,
          run: response.run,
        });
        startStreaming(response.thread?.id, response.run?.id);

        chatMutationThreadId.current = response.thread.id;
        updateQueryPath({ threadId: response.thread.id }, 'replace', false);

        void utils.hub.threads.refetch();
      } catch (error) {
        handleClientError({ error, title: 'Failed to run agent' });
      }
    },
  });

  const [collection, setCollection] = useState<
    z.infer<typeof SecretVaultWrapper>[] | null
  >(null);
  useEffect(() => {
    (async () => {
      const _collection = new SecretVaultWrapper(
        [
          {
            url: 'https://1.nildb.wehrenterprises.org',
            did: 'did:nil:testnet:nillion15lcjxgafgvs40rypvqu73gfvx6pkx7ugdja50d',
          },
          {
            url: 'https://2.nildb.wehrenterprises.org',
            did: 'did:nil:testnet:nillion1dfh44cs4h2zek5vhzxkfvd9w28s5q5cdepdvml',
          },
          {
            url: 'https://3.nildb.wehrenterprises.org',
            did: 'did:nil:testnet:nillion19t0gefm7pr6xjkq2sj40f0rs7wznldgfg4guue',
          },
        ],
        {
          secretKey: process.env.NEXT_PUBLIC_NILLION_ORG_SECRET_KEY,
          orgDid: process.env.NEXT_PUBLIC_NILLION_ORG_ID,
        },
        process.env.NEXT_PUBLIC_NILLION_SCHEMA_ID,
      );
      await _collection.init();
      setCollection(_collection);
    })();
  }, []);

  const isRunning =
    _chatMutation.isPending ||
    thread?.run?.status === 'queued' ||
    thread?.run?.status === 'in_progress';

  const isLoading = !!auth && !!threadId && !thread && !isRunning;

  const threadQuery = trpc.hub.thread.useQuery(
    {
      afterMessageId: thread?.latestMessageId,
      mockedAitpMessages: queryParams.mockedAitpMessages === 'true',
      runId: thread?.run?.id,
      threadId,
    },
    {
      enabled: !!auth && !!threadId,
      refetchInterval: isRunning ? 150 : 1500,
      retry: false,
    },
  );

  const logMessages = useMemo(() => {
    return (thread ? Object.values(thread.messagesById) : []).filter(
      (message) =>
        message.metadata?.message_type?.startsWith('system:') ||
        message.metadata?.message_type?.startsWith('agent:log'),
    );
  }, [thread]);

  const messages = useMemo(() => {
    return [
      ...(thread ? Object.values(thread.messagesById) : []),
      ...optimisticMessages.map((message) => message.data),
    ].filter(
      (message) =>
        showLogs ||
        !(
          message.metadata?.message_type?.startsWith('system:') ||
          message.metadata?.message_type?.startsWith('agent:log')
        ),
    );
  }, [thread, optimisticMessages, showLogs]);

  const files = useMemo(() => {
    const all = thread ? Object.values(thread.filesById) : [];
    const attachments: z.infer<typeof threadFileModel>[] = [];
    const outputs: z.infer<typeof threadFileModel>[] = [];

    for (const file of all) {
      const message = messages.find((message) =>
        message.attachments?.some(
          (attachment) => attachment.file_id === file.id,
        ),
      );
      if (message?.role === 'user') {
        attachments.push(file);
      } else {
        outputs.push(file);
      }
    }

    // Group outputs by filename and keep only the latest version
    const latestOutputsByFilename = outputs.reduce((acc, file) => {
      const existing = acc.get(file.filename);
      // Type guard to check if the file has created_at property
      const fileWithDate = file as z.infer<typeof threadFileModel> & {
        created_at?: string;
      };
      const existingWithDate = existing as z.infer<typeof threadFileModel> & {
        created_at?: string;
      };

      // If not available, we'll use the order in the array (latest files typically come last)
      if (
        !existing ||
        (fileWithDate.created_at &&
          existingWithDate.created_at &&
          fileWithDate.created_at > existingWithDate.created_at)
      ) {
        acc.set(file.filename, file);
      }
      return acc;
    }, new Map<string, z.infer<typeof threadFileModel>>());

    return {
      attachments,
      outputs: Array.from(latestOutputsByFilename.values()),
      total: attachments.length + latestOutputsByFilename.size,
    };
  }, [messages, thread]);

  const latestAssistantMessages = useMemo(() => {
    const result: z.infer<typeof threadMessageModel>[] = [];
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i]!;
      if (message.role === 'assistant') {
        result.unshift(message);
      } else {
        break;
      }
    }
    return result;
  }, [messages]);

  const {
    agentRequestsNeedingPermissions,
    setAgentRequestsNeedingPermissions,
    conditionallyProcessAgentRequests,
    iframePostMessage,
    onIframePostMessage,
  } = useAgentRequestsWithIframe(currentEntry, threadId);

  const [__view, __setView] = useState<RunView>();
  const view = (queryParams.view as RunView) ?? __view;
  const setView = useCallback(
    (value: RunView, updateUrl = false) => {
      __setView(value);

      if (updateUrl) {
        updateQueryPath(
          {
            view: value,
          },
          'replace',
          false,
        );
      }
    },
    [updateQueryPath],
  );

  const attachmentMaxSizeMegabytes = 50;
  const attachmentAcceptMimeTypes =
    currentEntry?.details.agent?.allow_message_attachments_accept_mime_types?.reduce(
      (result, type) => {
        result[type] = [];
        return result;
      },
      {} as Record<string, string[]>,
    );

  const deleteAttachment = useCallback(
    async (fileId: string) => {
      try {
        setAttachments((prev) => prev.filter((f) => f.id !== fileId));

        const { authorization, routerUrl } =
          await utils.hub.detailsForFileUpload.fetch();

        await fetch(`${routerUrl}/files/${fileId}`, {
          method: 'DELETE',
          headers: {
            Authorization: authorization,
          },
        });
      } catch (error) {
        console.error(error);
      }
    },
    [utils.hub.detailsForFileUpload],
  );

  const dropzoneOnDrop = useCallback(
    async (acceptedFiles: File[]) => {
      try {
        setIsUploadingAttachments(true);

        const { authorization, routerUrl } =
          await utils.hub.detailsForFileUpload.fetch();

        for (const file of acceptedFiles) {
          try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('purpose', 'assistants');

            const response = await fetch(`${routerUrl}/files`, {
              method: 'POST',
              headers: {
                Authorization: authorization,
              },
              body: formData,
            });

            const data = await response.json();
            const parsed = threadFileModel.safeParse(data);

            if (response.ok && parsed.data) {
              setAttachments((prev) => [...prev, parsed.data]);
              continue;
            }

            const error = apiErrorModel.safeParse(data);
            if (error.data) {
              throw new Error(error.data.detail);
            }

            throw new Error('Unknown error. Please try again later.');
          } catch (error) {
            handleClientError({
              error,
              title: 'Failed to upload file',
              description: (error as Error)?.message,
            });
          }
        }
      } catch (error) {
        handleClientError({ error });
      } finally {
        setIsUploadingAttachments(false);
      }
    },
    [utils.hub.detailsForFileUpload],
  );

  const dropzoneValidator = useCallback(() => {
    if (!currentEntry?.details.agent?.allow_message_attachments) {
      return {
        code: 'attachments-not-supported',
        message: `This agent does not support messages with file attachments`,
      };
    }
    return null;
  }, [currentEntry?.details.agent?.allow_message_attachments]);

  const dropzoneOnDropRejected = useCallback(
    (fileRejections: FileRejection[]) => {
      fileRejections.forEach((rejection) => {
        openToast({
          type: 'error',
          title: rejection.file.name,
          description: rejection.errors
            .map((error) => {
              if (error.code === 'file-too-large') {
                return `File size exceeds ${attachmentMaxSizeMegabytes} MB limit (${formatBytes(rejection.file.size)})`;
              }
              return error.message;
            })
            .join('. '),
        });
      });
    },
    [attachmentMaxSizeMegabytes],
  );

  const dropzone = useDropzone({
    multiple: true,
    noClick: true,
    accept: attachmentAcceptMimeTypes,
    maxSize: attachmentMaxSizeMegabytes * 1024 * 1024,
    validator: dropzoneValidator,
    onDrop: dropzoneOnDrop,
    onDropRejected: dropzoneOnDropRejected,
    onDragEnter: undefined,
    onDragOver: undefined,
    onDragLeave: undefined,
  });

  const onSubmit: SubmitHandler<FormSchema> = async (data) => {
    if (!data.new_message && !attachments.length) return;
    if (collection === null) return;

    console.log(`in onSubmit`);
    try {
      const storeResult: nilDbResult[] = await collection.writeToNodes([
        { _id: uuidv4(), message: { '%allot': data.new_message } },
      ]);

      const encodedResult = nilDbEncode(storeResult);
      console.log(`wrote to nildb: ${JSON.stringify(encodedResult, null, 4)}`);
      data.new_message = JSON.stringify(encodedResult);
    } catch (error) {
      console.error(
        `❌ Failed to write to nildb: ${data.new_message}`,
        error.message,
      );
    }

    await chatMutation.mutateAsync({
      ...data,
      attachments: attachments.map((attachment) => ({
        file_id: attachment.id,
      })),
    });
  };

  const onKeyDownContent: KeyboardEventHandler<HTMLTextAreaElement> = (
    event,
  ) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  const startNewThread = () => {
    updateQueryPath({
      threadId: null,
      view: null,
      showLogs: null,
      initialUserMessage: null,
    });
    clearOptimisticMessages();
    form.setValue('new_message', '');
    form.setFocus('new_message');
    setStreamingText('');
    setStreamingTextLatestChunk('');
  };

  useEffect(() => {
    if (
      threadQuery.data?.metadata.topic &&
      thread?.metadata.topic !== threadQuery.data?.metadata.topic
    ) {
      // This will trigger once the inferred thread topic generator background task has resolved
      void utils.hub.threads.refetch();
    }

    if (threadQuery.data) {
      setThread(threadQuery.data);
    }
  }, [setThread, threadQuery.data, thread?.metadata.topic, utils]);

  // SSE for streaming updates

  const stopStreaming = (stream: EventSource) => {
    stream.close();
    setIsStreaming(false);
    setStream(null);
    setStreamingText('');
    setStreamingTextLatestChunk('');
  };

  const startStreaming = (threadId: string, runId: string) => {
    if (!threadId) return;
    if (!runId) return;

    setIsStreaming(true);

    const eventSource = new EventSource(
      `/api/v1/threads/${threadId}/stream/${runId}`,
    );

    eventSource.addEventListener('message', (event) => {
      const data = JSON.parse(event.data);
      const eventType = data.event;
      switch (eventType) {
        case 'thread.message.delta':
          if (!data?.data?.delta?.content) return;
          const content = data.data.delta.content;
          if (content.length === 0 || !content[0]?.text?.value) return;
          const latestChunk = data.data.delta.content[0].text.value;
          setStreamingText((prevText) => prevText + latestChunk);
          setStreamingTextLatestChunk(latestChunk);

          // Force React to rerender immediately rather than batching
          setTimeout(() => {}, 0);
          break;

        case 'thread.message.completed':
          setStreamingText('');
          setStreamingTextLatestChunk('');
          break;
        case 'thread.run.completed':
        case 'thread.run.error':
        case 'thread.run.canceled':
        case 'thread.run.expired':
        case 'thread.run.requires_action':
          stopStreaming(eventSource);
          break;
      }
    });

    eventSource.onerror = (error) => {
      console.log('SSE error:', error);
      eventSource.close();
      setIsStreaming(false);
    };

    setStream(eventSource);

    return () => {
      eventSource.close();
    };
  };

  useEffect(() => {
    if (!isRunning) {
      if (stream) {
        stopStreaming(stream);
      }
    }
  }, [isRunning, stream]);

  useEffect(() => {
    if (threadQuery.error?.data?.code === 'FORBIDDEN') {
      openToast({
        type: 'error',
        title: 'Failed to load thread',
        description: `Your account doesn't have permission to access requested thread`,
      });
      updateQueryPath({ threadId: null });
    }
  }, [threadQuery.error, updateQueryPath]);

  useEffect(() => {
    const htmlFile = files.outputs.find(
      (file) => file.filename === 'index.html',
    );

    function parseHtmlContent(html: string) {
      html = html.replaceAll('{{%agent_id%}}', agentId);

      html = html.replace(
        /(src|href)="([^"]+)"/g,
        (_match, $attribute, $path) => {
          const attribute = $attribute as string;
          const path = $path as string;
          return `${attribute}="${rawFileUrlForEntry(
            {
              category: 'agent',
              namespace,
              name,
              version,
            },
            path,
          )}"`;
        },
      );

      return html;
    }

    if (htmlFile && typeof htmlFile.content === 'string') {
      setHtmlOutput(parseHtmlContent(htmlFile.content));
      setView('output');
    } else {
      setHtmlOutput('');
      setView('conversation');
    }
  }, [files, htmlOutput, agentId, setView, namespace, name, version]);

  useEffect(() => {
    if (currentEntry && auth) {
      form.setFocus('new_message');
    }
  }, [threadId, currentEntry, auth, form]);

  useEffect(() => {
    if (threadId !== chatMutationThreadId.current) {
      initialUserMessageSent.current = false;
      chatMutationThreadId.current = '';
      chatMutationStartedAt.current = null;
      clearOptimisticMessages();
    }
  }, [threadId, clearOptimisticMessages]);

  useEffect(() => {
    form.reset();
  }, [agentId, form]);

  useEffect(() => {
    setThreadsOpenForSmallScreens(false);
  }, [threadId]);

  useEffect(() => {
    const agentDetails = currentEntry?.details.agent;
    const initialUserMessage =
      queryParams.initialUserMessage || agentDetails?.initial_user_message;

    if (
      currentEntry &&
      initialUserMessage &&
      !threadId &&
      !initialUserMessageSent.current
    ) {
      initialUserMessageSent.current = true;
      void conditionallyProcessAgentRequests([
        {
          action: 'initial_user_message',
          input: {
            new_message: initialUserMessage,
          },
        },
      ]);
    }
  }, [
    queryParams,
    currentEntry,
    threadId,
    chatMutation,
    conditionallyProcessAgentRequests,
  ]);

  useEffect(() => {
    /*
      This allows child components within <AgentRunner> to add messages to the 
      current thread via Zustand:

      const addMessage = useThreadsStore((store) => store.addMessage);
    */

    setAddMessage(chatMutation.mutateAsync);

    () => {
      setAddMessage(undefined);
    };
  }, [chatMutation.mutateAsync, setAddMessage]);

  if (!currentEntry) {
    if (showLoadingPlaceholder) return <PlaceholderSection />;
    return null;
  }

  return (
    <>
      <Sidebar.Root>
        <ThreadsSidebar
          onRequestNewThread={startNewThread}
          openForSmallScreens={threadsOpenForSmallScreens}
          setOpenForSmallScreens={setThreadsOpenForSmallScreens}
        />

        <div {...dropzone.getRootProps({ className: s.dropzone })}>
          <Sidebar.Main fileDragIsActive={dropzone.isDragActive}>
            {isLoading ? (
              <PlaceholderStack style={{ marginBottom: 'auto' }} />
            ) : (
              <>
                {view === 'output' ? (
                  <>
                    <IframeWithBlob
                      html={htmlOutput}
                      height={currentEntry.details.agent?.html_height}
                      onPostMessage={onIframePostMessage}
                      postMessage={iframePostMessage}
                    />

                    {latestAssistantMessages.length > 0 &&
                      currentEntry.details.agent
                        ?.html_show_latest_messages_below && (
                        <ThreadMessages
                          grow={false}
                          messages={latestAssistantMessages}
                          scroll={false}
                          threadId={threadId}
                        />
                      )}
                  </>
                ) : (
                  <ThreadMessages
                    messages={messages}
                    streamingText={streamingText}
                    streamingTextLatestChunk={streamingTextLatestChunk}
                    threadId={threadId}
                    welcomeMessage={
                      <AgentWelcome currentEntry={currentEntry} />
                    }
                  />
                )}
              </>
            )}

            <Sidebar.MainStickyFooter>
              <Form onSubmit={form.handleSubmit(onSubmit)} ref={formRef}>
                <Flex direction="column" gap="m">
                  {isRunning && (
                    <ThreadThinking length={streamingText.length} />
                  )}

                  <InputTextarea
                    placeholder="Write your message and press enter..."
                    onKeyDown={onKeyDownContent}
                    disabled={!auth}
                    {...form.register('new_message')}
                  />

                  <input
                    type="file"
                    name="attachedFiles"
                    {...dropzone.getInputProps()}
                    className={s.fileInput}
                  />

                  {attachments.length > 0 && (
                    <Flex gap="s" wrap="wrap">
                      {attachments.map((file) => (
                        <Badge
                          key={file.id}
                          label={
                            <Flex as="span" align="center" gap="s">
                              {file.filename}
                              <Button
                                label="Delete Attachment"
                                size="x-small"
                                fill="ghost"
                                icon={<X />}
                                variant="secondary"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  void deleteAttachment(file.id);
                                }}
                              />
                            </Flex>
                          }
                          iconLeft={<Paperclip />}
                          variant="neutral-alpha"
                        />
                      ))}
                    </Flex>
                  )}

                  {auth ? (
                    <Flex align="start" gap="m" justify="space-between">
                      <BreakpointDisplay
                        show="larger-than-phone"
                        style={{ marginRight: 'auto' }}
                      >
                        <Text size="text-xs">
                          <b>Shift + Enter</b> to add a new line
                        </Text>
                      </BreakpointDisplay>

                      <Flex
                        align="start"
                        gap="s"
                        style={{ paddingRight: '0.15rem' }}
                      >
                        <BreakpointDisplay show="sidebar-small-screen">
                          <Tooltip asChild content="View all threads">
                            <Button
                              label="Select Thread"
                              icon={<List />}
                              size="small"
                              variant="secondary"
                              fill="ghost"
                              onClick={() =>
                                setThreadsOpenForSmallScreens(true)
                              }
                            />
                          </Tooltip>
                        </BreakpointDisplay>

                        <BreakpointDisplay show="sidebar-small-screen">
                          <Tooltip
                            asChild
                            content="View attached files & agent settings"
                          >
                            <Button
                              label={files.total.toString()}
                              iconLeft={<Folder />}
                              size="small"
                              variant="secondary"
                              fill="ghost"
                              style={{ paddingInline: '0.5rem' }}
                              onClick={() =>
                                setParametersOpenForSmallScreens(true)
                              }
                            />
                          </Tooltip>
                        </BreakpointDisplay>

                        {htmlOutput && (
                          <Tooltip
                            asChild
                            content={
                              view === 'output'
                                ? 'View conversation'
                                : 'View rendered output'
                            }
                          >
                            <Button
                              label="Toggle View"
                              icon={
                                <Eye
                                  weight={
                                    view === 'output' ? 'fill' : 'regular'
                                  }
                                />
                              }
                              size="small"
                              variant="secondary"
                              fill="ghost"
                              onClick={() =>
                                view === 'output'
                                  ? setView('conversation', true)
                                  : setView('output', true)
                              }
                            />
                          </Tooltip>
                        )}

                        <Tooltip
                          asChild
                          content={
                            showLogs ? 'Hide system logs' : 'Show system logs'
                          }
                        >
                          <Button
                            label={logMessages.length.toString()}
                            iconLeft={
                              <Info weight={showLogs ? 'fill' : 'regular'} />
                            }
                            size="small"
                            variant="secondary"
                            fill="ghost"
                            style={{ paddingInline: '0.5rem' }}
                            onClick={() =>
                              updateQueryPath(
                                { showLogs: showLogs ? undefined : 'true' },
                                'replace',
                                false,
                              )
                            }
                          />
                        </Tooltip>

                        {consumerModeEnabled && !embedded && (
                          <Tooltip asChild content="Inspect agent source">
                            <Button
                              label="Agent Source"
                              icon={<CodeBlock />}
                              size="small"
                              fill="ghost"
                              href={`https://app.near.ai${sourceUrlForEntry(currentEntry)}`}
                            />
                          </Tooltip>
                        )}

                        {currentEntry?.details.agent
                          ?.allow_message_attachments && (
                          <Tooltip asChild content="Attach files to message">
                            <Button
                              label="Attach Files"
                              icon={<Paperclip />}
                              size="small"
                              variant="secondary"
                              fill="ghost"
                              onClick={dropzone.open}
                              loading={isUploadingAttachments}
                            />
                          </Tooltip>
                        )}
                      </Flex>

                      <Button
                        label="Send Message"
                        type="submit"
                        icon={<ArrowRight weight="bold" />}
                        size="small"
                        loading={isRunning || isStreaming}
                      />
                    </Flex>
                  ) : (
                    <SignInPrompt />
                  )}
                </Flex>
              </Form>
            </Sidebar.MainStickyFooter>
          </Sidebar.Main>
        </div>

        <Sidebar.Sidebar
          openForSmallScreens={parametersOpenForSmallScreens}
          setOpenForSmallScreens={setParametersOpenForSmallScreens}
        >
          <Flex direction="column" gap="l">
            <Flex direction="column" gap="m">
              <Text size="text-xs" weight={600} uppercase>
                Output
              </Text>

              {isLoading ? (
                <PlaceholderStack />
              ) : (
                <>
                  {files.outputs.length ? (
                    <CardList>
                      {files.outputs.map((file) => (
                        <Card
                          padding="s"
                          gap="s"
                          key={file.id}
                          background="sand-2"
                          onClick={() => {
                            setOpenedFileId(file.id);
                          }}
                        >
                          <Flex direction="column" gap="xs">
                            <Flex align="center" gap="s">
                              <Text
                                size="text-s"
                                color="sand-12"
                                weight={500}
                                clampLines={1}
                                style={{ marginRight: 'auto' }}
                              >
                                {file.filename}
                              </Text>

                              <Text
                                size="text-xs"
                                noWrap
                                style={{ flexShrink: 0 }}
                              >
                                {formatBytes(file.bytes)}
                              </Text>
                            </Flex>

                            {'created_at' in file && file.created_at && (
                              <Text size="text-xs" color="sand-10">
                                {formatDistanceToNow(
                                  new Date(
                                    typeof file.created_at === 'string'
                                      ? file.created_at
                                      : file.created_at *
                                        (file.created_at < 10000000000
                                          ? 1000
                                          : 1),
                                  ),
                                  { addSuffix: true },
                                )}
                              </Text>
                            )}
                          </Flex>
                        </Card>
                      ))}
                    </CardList>
                  ) : (
                    <Text size="text-s" color="sand-10">
                      No generated files yet.
                    </Text>
                  )}
                </>
              )}
            </Flex>

            <Flex direction="column" gap="m">
              <Text size="text-xs" weight={600} uppercase>
                Attachments
              </Text>

              {isLoading ? (
                <PlaceholderStack />
              ) : (
                <>
                  {files.attachments.length ? (
                    <CardList>
                      {files.attachments.map((file) => (
                        <Card
                          padding="s"
                          gap="s"
                          key={file.id}
                          background="sand-2"
                          onClick={() => {
                            setOpenedFileId(file.id);
                          }}
                        >
                          <Flex align="center" gap="s">
                            <Text
                              size="text-s"
                              color="sand-12"
                              weight={500}
                              clampLines={1}
                              style={{ marginRight: 'auto' }}
                            >
                              {file.filename}
                            </Text>

                            <Text
                              size="text-xs"
                              noWrap
                              style={{ flexShrink: 0 }}
                            >
                              {formatBytes(file.bytes)}
                            </Text>
                          </Flex>
                        </Card>
                      ))}
                    </CardList>
                  ) : (
                    <Text size="text-s" color="sand-10">
                      You haven't attached any files yet.
                    </Text>
                  )}
                </>
              )}
            </Flex>

            {!consumerModeEnabled && (
              <EntryEnvironmentVariables
                entry={currentEntry}
                excludeQueryParamKeys={Object.keys(queryParams)}
              />
            )}
          </Flex>
        </Sidebar.Sidebar>
      </Sidebar.Root>

      <AgentPermissionsModal
        agent={currentEntry}
        onAllow={(requests) =>
          conditionallyProcessAgentRequests(requests, true)
        }
        requests={agentRequestsNeedingPermissions}
        clearRequests={() => setAgentRequestsNeedingPermissions(null)}
      />

      <ThreadFileModal filesById={thread?.filesById} />
    </>
  );
};
