"use client";

import { useEffect, useState } from "react";
import { type z } from "zod";
import { Button } from "~/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "~/components/ui/form";
import { Textarea } from "~/components/ui/textarea";
import { useZodForm } from "~/hooks/form";
import { useHandleRidirectFromWallet } from "~/hooks/misc";
import {
  CONVERSATION_PATH,
  useSendCompletionsRequest,
} from "~/hooks/mutations";
import { useListModels } from "~/hooks/queries";
import { chatCompletionsModel, type messageModel } from "~/lib/models";
import { Conversation } from "./bubble";
import { NearAccount } from "./near";
import { DropDownForm } from "./role";
import { SliderFormField } from "./slider";

const roles = [
  { label: "User", value: "user" },
  { label: "Assistant", value: "assistant" },
  { label: "System", value: "system" },
];

const providers = [
  { label: "Fireworks", value: "fireworks" },
  { label: "Hyperbolic", value: "hyperbolic" },
];

export function Chat() {
  useHandleRidirectFromWallet();

  const form = useZodForm(chatCompletionsModel);
  const chat = useSendCompletionsRequest();
  const listModels = useListModels();
  const [conversation, setConversation] = useState<
    z.infer<typeof messageModel>[]
  >([]);

  async function onSubmit(values: z.infer<typeof chatCompletionsModel>) {
    values.messages = [...conversation, ...values.messages];
    console.log("values", values);

    values.messages.map((m) => console.log(m.content));

    const resp = await chat.mutateAsync(values);
    const respMsg = resp.choices[0]!.message;

    setConversation(() => [...values.messages, respMsg]);
  }

  function clearConversation() {
    localStorage.removeItem(CONVERSATION_PATH);
    setConversation([]);
  }

  useEffect(() => {
    const currConv = localStorage.getItem(CONVERSATION_PATH);
    if (currConv) {
      console.log("currConv", currConv);

      const conv: unknown = JSON.parse(currConv);
      const parsed = chatCompletionsModel.parse(conv);
      setConversation(parsed.messages);
    }
  }, [setConversation]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <div className="flex flex-row">
          <div className="flex w-[20%] flex-col justify-between p-4">
            <div>History</div>
            <Button type="button" onClick={clearConversation}>
              Clear Conversation
            </Button>
          </div>

          <div className="flex h-screen w-[80%] flex-col justify-between bg-gray-100">
            <div className="flex-grow overflow-y-auto p-6">
              <Conversation messages={conversation} />
            </div>
            <div className="space-y-2 bg-white p-4">
              <FormField
                control={form.control}
                name="messages.0.content"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Textarea
                        placeholder="Type your message..."
                        className="w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button
                type="submit"
                className="w-full"
                disabled={chat.isPending === true}
              >
                Send
              </Button>
              {JSON.stringify(form.formState.errors) !== "{}" && (
                <div className="text-red-500">
                  {JSON.stringify(form.formState.errors)}
                </div>
              )}
            </div>
          </div>
          <div className="flex w-[20%] flex-col justify-between space-y-2 p-4">
            <div className="flex flex-col gap-3">
              <span>Parameters</span>
              <hr />
              <DropDownForm
                title="Provider"
                name="provider"
                defaultValue={"fireworks"}
                choices={providers}
              />
              <DropDownForm
                title="Model"
                name="model"
                defaultValue={
                  "accounts/fireworks/models/mixtral-8x22b-instruct"
                }
                choices={listModels.data ?? []}
              />
              <DropDownForm
                title="Role"
                name="messages.0.role"
                defaultValue={"user"}
                choices={roles}
              />
              <SliderFormField
                control={form.control}
                name="temperature"
                description="The temperature for sampling"
                max={2}
                min={0}
                step={0.01}
                defaultValue={0.1}
              />
              <SliderFormField
                control={form.control}
                name="max_tokens"
                description="The maximum number of tokens to generate"
                max={2048}
                min={1}
                step={1}
                defaultValue={64}
              />
            </div>
            <div>
              <NearAccount />
            </div>
          </div>
        </div>
      </form>
    </Form>
  );
}
