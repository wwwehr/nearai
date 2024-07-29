"use client";

import { useMutation } from "@tanstack/react-query";
import { type z } from "zod";
import { env } from "~/env";
import { type chatCompletionsModel } from "~/lib/models";
import usePersistingStore from "~/store/store";
import { api } from "~/trpc/react";

export const CONVERSATION_PATH = "current_conversation";
export const CALLBACK_URL = env.NEXT_PUBLIC_BASE_URL;
export const RECIPIENT = "ai.near";
export const NONCE = "12345678901234567890123456789012";

export function useSendCompletionsRequest() {
  const chatMut = api.router.chat.useMutation();

  return useMutation({
    mutationFn: async (values: z.infer<typeof chatCompletionsModel>) => {
      console.log("Storing in localStorage the conversation", values);
      localStorage.setItem(CONVERSATION_PATH, JSON.stringify(values));

      const resp = await chatMut.mutateAsync(values);

      values.messages = [...values.messages, resp.choices[0]!.message];

      localStorage.setItem(CONVERSATION_PATH, JSON.stringify(values));

      return values;
    },
  });
}

export function useChallengeRequest() {
  const challengeMut = api.router.challenge.useMutation();
  const store = usePersistingStore();
  return useMutation({
    mutationFn: async () => {
      const resp = await challengeMut.mutateAsync();

      store.setChallenge(resp.challenge);

      return resp.challenge;
    },
  });
}
