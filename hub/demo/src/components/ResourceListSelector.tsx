'use client';

import { Minus, Plus } from '@phosphor-icons/react';
import { useEffect, useRef } from 'react';
import { type z } from 'zod';

import { Flex } from '~/components/lib/Flex';
import { Input } from '~/components/lib/Input';
import { useRegistryEntriesSearch } from '~/hooks/registry';
import { type registryEntryModel } from '~/lib/models';
import { type RegistryCategory } from '~/server/api/routers/hub';
import { api } from '~/trpc/react';

import { Button } from './lib/Button';
import { Card, CardList } from './lib/Card';
import { PlaceholderStack } from './lib/Placeholder';
import { Text } from './lib/Text';
import { ResourceCard } from './ResourceCard';

export type ResourceListSelectorOnSelectItemHandler = (
  item: z.infer<typeof registryEntryModel>,
  selected: boolean,
) => unknown;

type Props = {
  category: RegistryCategory;
  description?: string;
  selectedIds: number[];
  onSelectItem: ResourceListSelectorOnSelectItemHandler;
};

export const ResourceListSelector = ({
  category,
  description,
  selectedIds,
  onSelectItem,
}: Props) => {
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const entriesQuery = api.hub.registryEntries.useQuery({ category });

  const { searched, searchQuery, setSearchQuery } = useRegistryEntriesSearch(
    entriesQuery.data,
  );

  searched?.sort((a, b) => {
    let sort = b.num_stars - a.num_stars;
    if (sort === 0) sort = a.name.localeCompare(b.name);
    return sort;
  });

  useEffect(() => {
    setTimeout(() => {
      searchInputRef.current?.focus();
    });
  }, []);

  return (
    <Flex direction="column" gap="l">
      {description && <Text>{description}</Text>}

      <Input
        type="search"
        name="search"
        placeholder="Search"
        value={searchQuery}
        onInput={(event) => setSearchQuery(event.currentTarget.value)}
        ref={searchInputRef}
      />

      {searched ? (
        <CardList>
          {searched.map((item) => (
            <ResourceCard
              linksOpenNewTab
              item={item}
              key={item.id}
              footer={
                <div>
                  {selectedIds.includes(item.id) ? (
                    <Button
                      iconLeft={<Minus />}
                      label="Remove"
                      variant="secondary"
                      size="small"
                      onClick={() => onSelectItem(item, false)}
                    />
                  ) : (
                    <Button
                      iconLeft={<Plus />}
                      label="Include"
                      variant="affirmative"
                      size="small"
                      onClick={() => onSelectItem(item, true)}
                    />
                  )}
                </div>
              }
            />
          ))}

          {!searched.length && (
            <Card>
              {searchQuery ? (
                <Text>No matching results. Try a different search?</Text>
              ) : (
                <Text>No options exist yet.</Text>
              )}
            </Card>
          )}
        </CardList>
      ) : (
        <PlaceholderStack />
      )}
    </Flex>
  );
};
