'use client';

import { ArrowRight } from '@phosphor-icons/react';
import { useMemo, useState } from 'react';
import { type z } from 'zod';

import { Button } from '~/components/lib/Button';
import { Flex } from '~/components/lib/Flex';
import { Grid } from '~/components/lib/Grid';
import { Input } from '~/components/lib/Input';
import { Table } from '~/components/lib/Table';
import { useTable } from '~/components/lib/Table/hooks';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { useDebouncedValue } from '~/hooks/debounce';
import { STANDARD_BENCHMARK_COLUMNS } from '~/lib/benchmarks';
import { benchmarkEvaluationsUrlForEntry } from '~/lib/entries';
import { type entryModel } from '~/lib/models';
import { type EntryCategory } from '~/server/api/routers/hub';
import { api } from '~/trpc/react';
import { wordsMatchFuzzySearch } from '~/utils/search';

type Props = {
  entry: z.infer<typeof entryModel>;
};

export const EntryEvaluationsTable = ({ entry }: Props) => {
  const [searchQuery, setSearchQuery] = useState('');
  const searchQueryDebounced = useDebouncedValue(searchQuery, 150);
  const evaluationsQuery = api.hub.evaluations.useQuery();

  const selectedBenchmarkColumns = [...STANDARD_BENCHMARK_COLUMNS];
  selectedBenchmarkColumns.sort();

  const searched = useMemo(() => {
    let evaluations = evaluationsQuery.data?.results;

    switch (entry.category as EntryCategory) {
      case 'agent':
        evaluations = evaluations?.filter((evaluation) => {
          return (
            evaluation.namespace === entry.namespace &&
            evaluation.agent === entry.name
          );
        });
        break;
      default:
        console.warn(
          `Unimplemented entry category for EntryEvaluationsTable: ${entry.category}`,
        );
    }

    if (!evaluations || !searchQueryDebounced) return evaluations;

    return evaluations.filter((evaluation) =>
      wordsMatchFuzzySearch(
        [
          evaluation.namespace,
          evaluation.agentPath ?? evaluation.agent,
          evaluation.provider,
          evaluation.model,
          evaluation.version,
        ],
        searchQueryDebounced,
      ),
    );
  }, [entry, evaluationsQuery.data, searchQueryDebounced]);

  const { sorted, ...tableProps } = useTable({
    data: searched,
    sortColumn: STANDARD_BENCHMARK_COLUMNS[0]!,
    sortOrder: 'DESCENDING',
  });

  return (
    <>
      <Grid
        columns="1fr 20rem"
        align="center"
        gap="m"
        phone={{ columns: '1fr' }}
      >
        <Flex align="center" gap="m">
          <Text size="text-l">Evaluations</Text>

          <Tooltip asChild content="View all benchmarks and evaluations">
            <Button
              label="View Evaluations"
              icon={<ArrowRight />}
              size="small"
              fill="outline"
              href={benchmarkEvaluationsUrlForEntry(entry)}
            />
          </Tooltip>
        </Flex>

        <Input
          type="search"
          name="search"
          placeholder="Search Evaluations"
          value={searchQuery}
          onInput={(event) => setSearchQuery(event.currentTarget.value)}
        />
      </Grid>

      {sorted?.length === 0 ? (
        <>
          {searchQueryDebounced ? (
            <Text>No matching results. Try a different search?</Text>
          ) : (
            <Text>No evaluations exist yet for this {entry.category}.</Text>
          )}
        </>
      ) : (
        <Table.Root {...tableProps}>
          <Table.Head>
            <Table.Row>
              <Table.HeadCell
                column="model"
                sortable
                style={{ minWidth: '12rem' }}
              >
                Model
              </Table.HeadCell>

              <Table.HeadCell column="provider" sortable>
                Provider
              </Table.HeadCell>

              <Table.HeadCell
                column="agentPath"
                sortable
                style={{ minWidth: '15rem' }}
              >
                Agent
              </Table.HeadCell>

              {selectedBenchmarkColumns.map((column) => (
                <Table.HeadCell column={column} sortable key={column}>
                  <Flex
                    as="span"
                    direction="column"
                    style={{ textTransform: 'none' }}
                  >
                    {column.includes('/') && (
                      <Text
                        as="span"
                        size="text-2xs"
                        color="current"
                        style={{
                          marginBottom: '-0.1rem',
                          display: 'inline-block',
                        }}
                      >
                        {column.split('/').slice(0, -1).join('/')}/
                      </Text>
                    )}
                    <Text as="span" size="text-s" weight={600} color="current">
                      {column.split('/').at(-1)}
                    </Text>
                  </Flex>
                </Table.HeadCell>
              ))}
            </Table.Row>
          </Table.Head>

          <Table.Body>
            {!sorted && <Table.PlaceholderRows />}

            {sorted?.map((evaluation, index) => (
              <Table.Row key={index}>
                <Table.Cell>
                  <Text size="text-s">{evaluation.model}</Text>
                </Table.Cell>

                <Table.Cell>
                  <Text size="text-s">{evaluation.provider}</Text>
                </Table.Cell>

                {evaluation.agentPath ? (
                  <Table.Cell href={`/agents/${evaluation.agentPath}`}>
                    <Text size="text-s" weight={500} color="sand-12">
                      {evaluation.agentPath}
                    </Text>
                  </Table.Cell>
                ) : (
                  <Table.Cell>
                    <Text size="text-xs" color="sand-8">
                      --
                    </Text>
                  </Table.Cell>
                )}

                {selectedBenchmarkColumns.map((column) => (
                  <Table.Cell key={column}>
                    <Tooltip content={column}>
                      {typeof evaluation[column] === 'number' ? (
                        <Text size="text-s" color="sand-12">
                          {evaluation[column]}%
                        </Text>
                      ) : (
                        <>
                          {evaluation[column] ? (
                            <Text size="text-s">{evaluation[column]}</Text>
                          ) : (
                            <Text size="text-xs" color="sand-8">
                              --
                            </Text>
                          )}
                        </>
                      )}
                    </Tooltip>
                  </Table.Cell>
                ))}
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      )}
    </>
  );
};
