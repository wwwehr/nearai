import { type FinalExecutionOutcome } from '@near-wallet-selector/core';
import { useCallback, useEffect, useState } from 'react';
import { type z } from 'zod';

import {
  type AgentRequest,
  checkAgentPermissions,
} from '~/components/AgentPermissionsModal';
import { type IframePostMessageEventHandler } from '~/components/lib/IframeWithBlob';
import {
  agentWalletTransactionRequestModel,
  agentWalletViewRequestModel,
  chatWithAgentModel,
  type entryModel,
} from '~/lib/models';
import { useNearStore } from '~/stores/near';
import { useWalletStore } from '~/stores/wallet';
import { type api } from '~/trpc/react';
import { unreachable } from '~/utils/unreachable';

import { useQueryParams } from './url';

const PENDING_TRANSACTION_KEY = 'agent-transaction-request-pending-connection';

export function useAgentRequestsWithIframe(
  currentEntry: z.infer<typeof entryModel> | undefined,
  chatMutation: ReturnType<typeof api.hub.chatWithAgent.useMutation>,
  environmentId: string | null | undefined,
) {
  const { queryParams, updateQueryPath } = useQueryParams([
    'account_id',
    'environmentId',
    'public_key',
    'transactionHashes',
    'transactionRequestId',
  ]);
  const wallet = useWalletStore((store) => store.wallet);
  const walletSignInModal = useWalletStore((store) => store.modal);
  const nearViewAccount = useNearStore((store) => store.viewAccount);
  const [iframePostMessage, setIframePostMessage] = useState<unknown>(null);
  const [agentRequestsNeedingPermissions, setAgentRequestsNeedingPermissions] =
    useState<AgentRequest[] | null>(null);

  const handleWalletTransactionResponse = useCallback(
    (options: {
      result: FinalExecutionOutcome[] | string;
      requestId?: string;
    }) => {
      const transactionHashes =
        typeof options.result === 'string'
          ? options.result.split(',')
          : options.result.map((outcome) => outcome.transaction_outcome.id);

      setIframePostMessage({
        action: 'near_call_response',
        requestId: options.requestId,
        result: {
          transactionHashes,
        },
      });

      updateQueryPath(
        {
          account_id: undefined,
          public_key: undefined,
          transactionHashes: undefined,
          transactionRequestId: undefined,
        },
        'replace',
        false,
      );
    },
    [updateQueryPath],
  );

  const conditionallyProcessAgentRequests = async (
    requests: AgentRequest[],
    allowedBypass?: boolean,
  ) => {
    if (!currentEntry) return;

    const permissionsCheck = checkAgentPermissions(currentEntry, requests);

    if (allowedBypass ?? permissionsCheck.allowed) {
      requests.forEach(async (request) => {
        if ('agent_id' in request) {
          const response = await chatMutation.mutateAsync(request);
          updateQueryPath(
            { environmentId: response.environmentId },
            'replace',
            false,
          );
        } else {
          if (wallet) {
            try {
              const callbackUrl = new URL(window.location.href);
              if (request.requestId) {
                callbackUrl.searchParams.set(
                  'transactionRequestId',
                  request.requestId,
                );
              }

              const result = await wallet.signAndSendTransactions({
                transactions: [
                  {
                    actions: [
                      {
                        params: {
                          args: request.params,
                          deposit: request.deposit,
                          gas: request.gas,
                          methodName: request.method,
                        },
                        type: 'FunctionCall',
                      },
                    ],
                    receiverId: request.recipient,
                  },
                ],
                callbackUrl: callbackUrl.toString(),
              });

              if (result) {
                handleWalletTransactionResponse({
                  result,
                  requestId: request.requestId,
                });
              }
            } catch (error) {
              console.error(error);
            }
          } else {
            localStorage.setItem(
              PENDING_TRANSACTION_KEY,
              JSON.stringify(request),
            );
            walletSignInModal!.show();
          }
        }
      });
    } else {
      setAgentRequestsNeedingPermissions(requests);
    }
  };

  const onIframePostMessage: IframePostMessageEventHandler<{
    action:
      | 'near_call'
      | 'near_view'
      | 'remote_agent_run'
      | 'refresh_environment_id';
    data: unknown;
  }> = async (event) => {
    try {
      const action = event.data.action;

      if (action === 'near_call') {
        const request = agentWalletTransactionRequestModel.parse(
          event.data.data,
        );
        void conditionallyProcessAgentRequests([request]);
      } else if (action === 'near_view') {
        const request = agentWalletViewRequestModel.parse(event.data.data);

        const result: unknown = await nearViewAccount!.viewFunction({
          contractId: request.recipient,
          methodName: request.method,
          args: request.params,
        });

        setIframePostMessage({
          action: 'near_view_response',
          requestId: request.requestId,
          result,
        });
      } else if (action === 'refresh_environment_id') {
        const chat = chatWithAgentModel.parse(event.data.data);
        if (chat.environment_id) {
          updateQueryPath(
            { environmentId: chat.environment_id },
            'replace',
            false,
          );
        }
      } else if (action === 'remote_agent_run') {
        const chat = chatWithAgentModel.parse(event.data.data);
        chat.max_iterations = Number(chat.max_iterations) || 1;
        chat.environment_id = chat.environment_id ?? environmentId;
        void conditionallyProcessAgentRequests([chat]);
      } else {
        unreachable(action);
      }
    } catch (error) {
      console.error(`Unable to handle message in onIframePostMessage()`, error);
    }
  };

  useEffect(() => {
    if (currentEntry && wallet) {
      try {
        const rawRequest = localStorage.getItem(PENDING_TRANSACTION_KEY);
        if (rawRequest) {
          const request = JSON.parse(rawRequest) as AgentRequest;
          void conditionallyProcessAgentRequests([request], true);
        }
      } catch (error) {
        console.error(error);
      }

      localStorage.removeItem(PENDING_TRANSACTION_KEY);
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentEntry, wallet]);

  useEffect(() => {
    if (queryParams.transactionHashes) {
      handleWalletTransactionResponse({
        result: queryParams.transactionHashes,
        requestId: queryParams.transactionRequestId,
      });
    }
  }, [queryParams, handleWalletTransactionResponse]);

  return {
    agentRequestsNeedingPermissions,
    conditionallyProcessAgentRequests,
    iframePostMessage,
    onIframePostMessage,
    setAgentRequestsNeedingPermissions,
  };
}
