'use client';

import { Eye, Minus, Plus } from '@phosphor-icons/react';
import Head from 'next/head';
import Link from 'next/link';
import { type ChangeEventHandler, useEffect, useMemo, useState } from 'react';
import { type z } from 'zod';

import { Button } from '~/components/lib/Button';
import { Card, CardList } from '~/components/lib/Card';
import { Checkbox, CheckboxGroup } from '~/components/lib/Checkbox';
import { Dialog } from '~/components/lib/Dialog';
import { Flex } from '~/components/lib/Flex';
import { Grid } from '~/components/lib/Grid';
import { Input } from '~/components/lib/Input';
import { PlaceholderStack } from '~/components/lib/Placeholder';
import { Sidebar } from '~/components/lib/Sidebar';
import { Table } from '~/components/lib/Table';
import { useTable } from '~/components/lib/Table/hooks';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import {
  ResourceListSelector,
  type ResourceListSelectorOnSelectItemHandler,
} from '~/components/ResourceListSelector';
import { useDebouncedValue } from '~/hooks/debounce';
import { useQueryParams } from '~/hooks/url';
import { STANDARD_BENCHMARK_COLUMNS } from '~/lib/benchmarks';
import { type registryEntryModel } from '~/lib/models';
import { api } from '~/trpc/react';
import { wordsMatchFuzzySearch } from '~/utils/search';

/*
  TODO:

  - Add evaluation summary table to agent details summary page (with CTA to view evaluations page)
  - Come up with solution for sticky table header since position sticky won't be an option anymore
*/

export default function EvaluationsPage() {
  const { updateQueryPath, queryParams } = useQueryParams([
    'benchmarks',
    'columns',
    'search',
  ]);
  const [benchmarkSelectorIsOpen, setBenchmarkSelectorIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState(queryParams.search ?? '');
  const [sidebarIsOpenForSmallerScreens, setSidebarIsOpenForSmallerScreens] =
    useState(false);
  const searchQueryDebounced = useDebouncedValue(searchQuery, 150);

  const evaluationsQuery = api.hub.evaluations.useQuery();
  const benchmarksQuery = api.hub.registryEntries.useQuery({
    category: 'benchmark',
  });

  const selectedBenchmarkIds = useMemo(() => {
    return queryParams.benchmarks
      ? queryParams.benchmarks.split(',').map((id) => parseInt(id))
      : [];
  }, [queryParams.benchmarks]);

  const selectedBenchmarkColumns = useMemo(() => {
    const columns = queryParams.columns
      ? queryParams.columns.split(',')
      : selectedBenchmarkIds.length > 0
        ? []
        : STANDARD_BENCHMARK_COLUMNS;

    columns.sort();

    return columns;
  }, [queryParams.columns, selectedBenchmarkIds]);

  const selectedBenchmarks = useMemo(() => {
    return benchmarksQuery.data?.filter((item) =>
      selectedBenchmarkIds.includes(item.id),
    );
  }, [benchmarksQuery.data, selectedBenchmarkIds]);

  const searched = useMemo(() => {
    const evaluations = evaluationsQuery.data?.results;

    if (!evaluations || !searchQueryDebounced) return evaluations;

    return evaluations.filter((item) =>
      wordsMatchFuzzySearch(
        [
          item.namespace,
          item.agentPath ?? item.agent,
          item.provider,
          item.model,
        ],
        searchQueryDebounced,
      ),
    );
  }, [evaluationsQuery.data, searchQueryDebounced]);

  const { sorted, ...tableProps } = useTable({
    data: searched,
    sortColumn: 'live_bench/average',
    sortOrder: 'DESCENDING',
  });

  const columnsForBenchmark = (
    benchmark: z.infer<typeof registryEntryModel>,
  ) => {
    if (!evaluationsQuery.data) return [];

    const columns = evaluationsQuery.data.benchmarkColumns.filter(
      (column) =>
        column === benchmark.name || column.startsWith(`${benchmark.name}/`),
    );

    if (!columns.length) {
      columns.push(benchmark.name);
    }

    return columns;
  };

  const toggleAllColumnsForBenchmark = (
    benchmark: z.infer<typeof registryEntryModel>,
  ) => {
    let columns = queryParams.columns?.split(',') ?? [];
    const relatedColumns = columnsForBenchmark(benchmark);
    const relatedColumnActiveColumn = columns.find((column) =>
      relatedColumns.includes(column),
    );

    if (relatedColumnActiveColumn) {
      columns = columns.filter((column) => !relatedColumns.includes(column));
    } else {
      columns = [...new Set([...columns, ...relatedColumns])];
    }

    updateQueryPath({ columns: columns.join(',') }, 'replace');
  };

  const onFilteredBenchmarkColumnChange: ChangeEventHandler<
    HTMLInputElement
  > = (event) => {
    let columns = [...selectedBenchmarkColumns];

    if (event.target.checked) {
      columns.push(event.target.value);
    } else {
      columns = columns.filter((benchmark) => benchmark !== event.target.value);
    }

    updateQueryPath({ columns: columns.join(',') }, 'replace');
  };

  const onSelectBenchmark: ResourceListSelectorOnSelectItemHandler = (
    benchmark,
    selected,
  ) => {
    let ids = [...selectedBenchmarkIds];
    let columns = queryParams.columns?.split(',') ?? [];
    const relatedColumns = columnsForBenchmark(benchmark);

    if (selected) {
      ids.push(benchmark.id);
      columns = [...new Set([...columns, ...relatedColumns])];
    } else {
      ids = ids.filter((id) => id !== benchmark.id);
      columns = columns.filter((column) => !relatedColumns.includes(column));
    }

    updateQueryPath(
      { benchmarks: ids.join(','), columns: columns.join(',') },
      'replace',
    );
    setBenchmarkSelectorIsOpen(false);
  };

  useEffect(() => {
    if (
      queryParams.benchmarks &&
      selectedBenchmarkColumns.length === 0 &&
      selectedBenchmarks
    ) {
      selectedBenchmarks.forEach((benchmark) => {
        toggleAllColumnsForBenchmark(benchmark);
      });
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBenchmarks, selectedBenchmarkColumns]);

  return (
    <>
      <Head>
        <title>Evaluations</title>
      </Head>

      <Sidebar.Root>
        <Sidebar.Sidebar
          openForSmallScreens={sidebarIsOpenForSmallerScreens}
          setOpenForSmallScreens={setSidebarIsOpenForSmallerScreens}
        >
          <Flex align="center" gap="s">
            <Text size="text-xs" weight={500} uppercase>
              Benchmarks
            </Text>

            <Tooltip asChild content="Include a benchmark">
              <Button
                label="Include Benchmark"
                icon={<Plus weight="bold" />}
                variant="affirmative"
                size="x-small"
                fill="ghost"
                onClick={() => setBenchmarkSelectorIsOpen(true)}
              />
            </Tooltip>
          </Flex>

          {selectedBenchmarks ? (
            <>
              {selectedBenchmarks.length > 0 ? (
                <Sidebar.SidebarContentBleed>
                  <CardList>
                    {selectedBenchmarks.map((benchmark) => (
                      <Card padding="m" background="sand-2" key={benchmark.id}>
                        <Flex gap="xs">
                          <Flex
                            direction="column"
                            style={{ marginRight: 'auto' }}
                          >
                            <Text size="text-s" weight={500} color="sand-12">
                              {benchmark.name} {benchmark.version}
                            </Text>
                            <Link
                              href={`/profiles/${benchmark.namespace}`}
                              target="_blank"
                            >
                              <Text size="text-xs">@{benchmark.namespace}</Text>
                            </Link>
                          </Flex>

                          <Tooltip asChild content="Toggle all columns">
                            <Button
                              label="Toggle all columns"
                              icon={<Eye weight="duotone" />}
                              size="x-small"
                              fill="ghost"
                              onClick={() =>
                                toggleAllColumnsForBenchmark(benchmark)
                              }
                            />
                          </Tooltip>

                          <Tooltip asChild content="Remove benchmark">
                            <Button
                              label="Remove benchmark"
                              icon={<Minus />}
                              size="x-small"
                              fill="ghost"
                              onClick={() =>
                                onSelectBenchmark(benchmark, false)
                              }
                            />
                          </Tooltip>
                        </Flex>

                        <CheckboxGroup name="columns">
                          {columnsForBenchmark(benchmark).map((column) => (
                            <Flex
                              as="label"
                              align="center"
                              gap="s"
                              key={column}
                            >
                              <Checkbox
                                name={`columns-${column}`}
                                value={column}
                                checked={selectedBenchmarkColumns.includes(
                                  column,
                                )}
                                onChange={onFilteredBenchmarkColumnChange}
                              />
                              <Text as="span" size="text-xs" color="sand-12">
                                {column.replace(`${benchmark.name}/`, '')}
                              </Text>
                            </Flex>
                          ))}
                        </CheckboxGroup>
                      </Card>
                    ))}
                  </CardList>
                </Sidebar.SidebarContentBleed>
              ) : (
                <Text size="text-s">
                  Include benchmarks to view specific evaluation metrics
                  (columns).
                </Text>
              )}
            </>
          ) : (
            <PlaceholderStack />
          )}
        </Sidebar.Sidebar>

        <Sidebar.Main>
          <Grid
            columns="1fr 20rem"
            align="center"
            gap="m"
            phone={{ columns: '1fr' }}
          >
            <Text as="h1" size="text-2xl">
              Evaluations
            </Text>

            <Input
              type="search"
              name="search"
              placeholder="Search Evaluations"
              value={searchQuery}
              onInput={(event) => setSearchQuery(event.currentTarget.value)}
            />
          </Grid>

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
                      <Text
                        as="span"
                        size="text-s"
                        weight={600}
                        color="current"
                      >
                        {column.split('/').at(-1)}
                      </Text>
                    </Flex>
                  </Table.HeadCell>
                ))}
              </Table.Row>
            </Table.Head>

            <Table.Body>
              {!evaluationsQuery.data && <Table.PlaceholderRows />}

              {sorted.map((item, index) => (
                <Table.Row key={index}>
                  <Table.Cell>
                    <Text size="text-s">{item.model}</Text>
                  </Table.Cell>

                  <Table.Cell>
                    <Text size="text-s">{item.provider}</Text>
                  </Table.Cell>

                  {item.agentPath ? (
                    <Table.Cell href={`/agents/${item.agentPath}`}>
                      <Text size="text-s" weight={500} color="sand-12">
                        {item.agentPath}
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
                        {typeof item[column] === 'number' ? (
                          <Text size="text-s" color="sand-12">
                            {item[column]}%
                          </Text>
                        ) : (
                          <>
                            {item[column] ? (
                              <Text size="text-s">{item[column]}</Text>
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

          {evaluationsQuery.data && sorted.length === 0 && (
            <>
              {searchQuery ? (
                <Text>No matching results. Try a different search?</Text>
              ) : (
                <Text>No evaluations exist yet.</Text>
              )}
            </>
          )}
        </Sidebar.Main>
      </Sidebar.Root>

      <Dialog.Root
        open={benchmarkSelectorIsOpen}
        onOpenChange={setBenchmarkSelectorIsOpen}
      >
        <Dialog.Content title="Benchmarks" align="stretch">
          <ResourceListSelector
            category="benchmark"
            description="Select benchmarks to include in the evaluations table."
            selectedIds={selectedBenchmarkIds}
            onSelectItem={onSelectBenchmark}
          />
        </Dialog.Content>
      </Dialog.Root>
    </>
  );
}
