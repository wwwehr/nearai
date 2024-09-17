'use client';

import { Eye, EyeSlash, Minus, Plus } from '@phosphor-icons/react';
import Head from 'next/head';
import { type ChangeEventHandler, Fragment, useState } from 'react';

import { Button } from '~/components/lib/Button';
import { Checkbox, CheckboxGroup } from '~/components/lib/Checkbox';
import { Combobox } from '~/components/lib/Combobox';
import { Flex } from '~/components/lib/Flex';
import { Grid } from '~/components/lib/Grid';
import { Sidebar } from '~/components/lib/Sidebar';
import { Table } from '~/components/lib/Table';
import { useTable } from '~/components/lib/Table/hooks';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { useQueryParams } from '~/hooks/url';
import { api } from '~/trpc/react';

const DEFAULT_BENCHMARKS = ['live_bench/average', 'mbpp'];

export default function BenchmarksPage() {
  const { updateQueryPath, queryParams } = useQueryParams(['columns']);
  const [showAllBenchmarkColumns, setShowAllBenchmarkColumns] = useState(false);

  const activeBenchmarkColumns = queryParams.columns
    ? queryParams.columns.split(',')
    : DEFAULT_BENCHMARKS;

  const evaluationsQuery = api.hub.evaluations.useQuery();

  const benchmarkColumns = [
    ...new Set([
      ...activeBenchmarkColumns,
      ...(evaluationsQuery.data?.benchmarkColumns ?? []),
    ]),
  ];
  benchmarkColumns?.sort();
  const filteredBenchmarkColumns = showAllBenchmarkColumns
    ? benchmarkColumns
    : benchmarkColumns?.filter((column) =>
        activeBenchmarkColumns.includes(column),
      );

  const [sidebarIsOpenForSmallerScreens, setSidebarIsOpenForSmallerScreens] =
    useState(false);

  // const { searched, searchQuery, setSearchQuery } = useRegistryEntriesSearch(
  //   evaluationsQuery.data,
  // );

  const { sorted, ...tableProps } = useTable({
    data: evaluationsQuery.data?.results,
    sortColumn: 'live_bench/average',
    sortOrder: 'DESCENDING',
  });

  const onFilteredBenchmarkColumnChange: ChangeEventHandler<
    HTMLInputElement
  > = (event) => {
    let columns = [...activeBenchmarkColumns];

    if (event.target.checked) {
      columns.push(event.target.value);
    } else {
      columns = columns.filter((benchmark) => benchmark !== event.target.value);
    }

    updateQueryPath({ columns: columns.join(',') });
  };

  return (
    <>
      <Head>
        <title>Benchmarks</title>
      </Head>

      <Sidebar.Root>
        <Sidebar.Sidebar
          openForSmallScreens={sidebarIsOpenForSmallerScreens}
          setOpenForSmallScreens={setSidebarIsOpenForSmallerScreens}
        >
          <Flex align="center" gap="s">
            <Text size="text-xs" weight={600} uppercase>
              Selected
            </Text>

            {showAllBenchmarkColumns ? (
              <Tooltip asChild content="Hide unselected benchmarks">
                <Button
                  label="Collapse Benchmarks"
                  icon={<Minus weight="bold" />}
                  size="x-small"
                  fill="ghost"
                  onClick={() => setShowAllBenchmarkColumns(false)}
                />
              </Tooltip>
            ) : (
              <Tooltip asChild content="Show all selectable benchmarks">
                <Button
                  label="Show Benchmarks"
                  icon={<Plus weight="bold" />}
                  variant="affirmative"
                  size="x-small"
                  fill="ghost"
                  onClick={() => setShowAllBenchmarkColumns(true)}
                />
              </Tooltip>
            )}
          </Flex>

          <CheckboxGroup name="columns">
            {filteredBenchmarkColumns?.map((column) => (
              <Flex as="label" align="baseline" gap="s" key={column}>
                <Checkbox
                  name={`columns-${column}`}
                  value={column}
                  type="checkbox"
                  checked={activeBenchmarkColumns.includes(column)}
                  onChange={onFilteredBenchmarkColumnChange}
                />
                <Flex as="span" direction="column">
                  <Text size="text-s" color="sand-12">
                    {column}
                  </Text>
                </Flex>
              </Flex>
            ))}
          </CheckboxGroup>
        </Sidebar.Sidebar>

        <Sidebar.Main>
          <Grid
            columns="1fr 20rem"
            align="center"
            gap="m"
            phone={{ columns: '1fr' }}
          >
            <Text as="h1" size="text-2xl">
              Benchmarks{' '}
              {evaluationsQuery.data && (
                <Text as="span" size="text-2xl" color="sand-10" weight={400}>
                  ({evaluationsQuery.data.results.length})
                </Text>
              )}
            </Text>

            {/* <Input
          type="search"
          name="search"
          placeholder={`Search ${title}`}
          value={searchQuery}
          onInput={(event) => setSearchQuery(event.currentTarget.value)}
        /> */}
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

                {activeBenchmarkColumns.map((column) => (
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
                            marginBottom: '-0.2rem',
                            display: 'inline-block',
                          }}
                        >
                          {column.split('/').slice(0, -1).join('/')}
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

                  {activeBenchmarkColumns.map((column) => (
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
        </Sidebar.Main>
      </Sidebar.Root>
    </>
  );
}
