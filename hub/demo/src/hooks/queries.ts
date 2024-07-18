import { useQuery } from "@tanstack/react-query";
import { api } from "~/trpc/react";

export function useListModels() {
  const listModels = api.router.listModels.useQuery();

  return useQuery({
    queryKey: ["listModels"],
    queryFn: () => {
      console.log("listModels", listModels.data);

      const m = listModels.data?.data.map((m) => {
        return { label: m.id, value: m.id };
      });

      console.log("models", m);

      return m;
    },
    enabled: !!listModels.data,
  });
}
