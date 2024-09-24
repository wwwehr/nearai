import { useParams } from 'next/navigation';
import { useMemo, useState } from 'react';
import { type z } from 'zod';

import { type entriesModel, type EntryCategory } from '~/lib/models';
import { api } from '~/trpc/react';
import { wordsMatchFuzzySearch } from '~/utils/search';

import { useDebouncedValue } from './debounce';

export function useEntryParams() {
  const { namespace, name, version } = useParams();

  return {
    namespace: namespace as string,
    name: name as string,
    version: version as string,
  };
}

export function useCurrentEntry(category: EntryCategory) {
  const { namespace, name, version } = useEntryParams();

  const entriesQuery = api.hub.entries.useQuery({
    category,
    namespace,
    showLatestVersion: false,
  });

  const currentVersions = entriesQuery.data?.filter(
    (item) => item.name === name,
  );

  const currentEntry = currentVersions?.find(
    (item) => item.version === version,
  );

  return {
    currentEntry,
    currentEntryIsHidden: !!entriesQuery.data && !currentEntry,
    currentVersions,
  };
}

export function useEntriesSearch(
  data: z.infer<typeof entriesModel> | undefined,
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
