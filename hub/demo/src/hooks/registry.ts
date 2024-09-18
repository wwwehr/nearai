import { useParams } from 'next/navigation';
import { useMemo, useState } from 'react';
import { type z } from 'zod';

import { type registryEntriesModel } from '~/lib/models';
import { type RegistryCategory } from '~/server/api/routers/hub';
import { api } from '~/trpc/react';
import { wordsMatchFuzzySearch } from '~/utils/search';

import { useDebouncedValue } from './debounce';

export function useRegistryEntryParams() {
  const { namespace, name, version } = useParams();

  return {
    namespace: namespace as string,
    name: name as string,
    version: version as string,
  };
}

export function useCurrentRegistryEntry(category: RegistryCategory) {
  const { namespace, name, version } = useRegistryEntryParams();

  const list = api.hub.registryEntries.useQuery({
    category,
    namespace,
    showLatestVersion: false,
  });

  const currentVersions = list.data?.filter((item) => item.name === name);

  const currentResource = currentVersions?.find(
    (item) => item.version === version,
  );

  return {
    currentResource,
    currentVersions,
  };
}

export function useRegistryEntriesSearch(
  data: z.infer<typeof registryEntriesModel> | undefined,
) {
  const [searchQuery, setSearchQuery] = useState('');
  const searchQueryDebounced = useDebouncedValue(searchQuery, 150);

  const searched = useMemo(() => {
    if (!data || !searchQueryDebounced) return data;

    return data.filter((item) =>
      wordsMatchFuzzySearch(
        [item.namespace, item.name, ...item.tags],
        searchQueryDebounced,
      ),
    );
  }, [data, searchQueryDebounced]);

  return {
    searched,
    searchQuery,
    setSearchQuery,
  };
}
