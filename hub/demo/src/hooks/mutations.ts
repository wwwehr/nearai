"use client";

import { useMutation } from "@tanstack/react-query";
import { type z } from "zod";
import { useWalletSelector } from "~/context/WalletSelectorContext";
import { env } from "~/env";
import { type chatCompletionsModel } from "~/lib/models";
import { api } from "~/trpc/react";

export const CONVERSATION_PATH = "current_conversation";
export const CALLBACK_URL = `${env.NEXT_PUBLIC_BASE_URL}/?action=send`;
export const PLAIN_MSG = "test message to sign";
export const CURRENT_AUTH = "current_auth";

export function useSendCompletionsRequest() {
  const chatMut = api.router.chat.useMutation();
  const walletSelector = useWalletSelector();

  return useMutation({
    mutationFn: async (values: z.infer<typeof chatCompletionsModel>) => {
      console.log("values", values);

      console.log("Storing in localStorage the conversation");
      localStorage.setItem(CONVERSATION_PATH, JSON.stringify(values));

      const currAuth = localStorage.getItem(CURRENT_AUTH);
      if (!currAuth) {
        // TODO: or expired
        try {
          const w = await walletSelector.selector.wallet();

          await w.signMessage({
            // Sign message is gonna redirect the full dom to the wallet provider, losing current state.
            // Handle Callback_url to get back here with a valid currSign and avoid that `if` condition.
            message: PLAIN_MSG,
            nonce: Buffer.from("1".repeat(32)),
            recipient: "ai.near",
            callbackUrl: CALLBACK_URL,
          });
        } catch (e) {
          walletSelector.modal.show();
        }
      }

      return await chatMut.mutateAsync(values);
    },
  });
}
