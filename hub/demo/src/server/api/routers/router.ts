import { env } from "~/env";
import {
  challengeResponseModel,
  chatCompletionsModel,
  chatResponseModel,
  listModelsResponseModel,
} from "~/lib/models";

import {
  createTRPCRouter,
  protectedProcedure,
  publicProcedure,
} from "~/server/api/trpc";

export const routerRouter = createTRPCRouter({
  listModels: publicProcedure.query(async () => {
    const u = env.ROUTER_URL + "/models";

    const response = await fetch(u);
    const resp: unknown = await response.json();

    return listModelsResponseModel.parse(resp);
  }),

  chat: protectedProcedure
    .input(chatCompletionsModel)
    .mutation(async ({ ctx, input }) => {
      const u = env.ROUTER_URL + "/chat/completions";

      const response = await fetch(u, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: ctx.Authorization!,
        },
        body: JSON.stringify(input),
      });

      // check for errors
      if (!response.ok) {
        throw new Error(
          "Failed to send chat completions, status: " +
            response.status +
            " " +
            response.statusText,
        );
      }

      const resp: unknown = await response.json();

      return chatResponseModel.parse(resp);
    }),

  challenge: publicProcedure.mutation(async () => {
    const u = env.ROUTER_URL + "/challenge";

    const response = await fetch(u, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      console.error("Failed to get challenge", response);
      throw new Error("Failed to get challenge");
    }

    const resp: unknown = await response.json();

    return challengeResponseModel.parse(resp);
  }),
});
