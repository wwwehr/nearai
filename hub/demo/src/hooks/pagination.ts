import { useCallback, useEffect, useMemo, useState } from 'react';

import { useQueryParams } from './url';

type UseClientPaginationOptions<
  T extends Record<string, unknown>[] | undefined,
> = {
  data: T;
  itemsPerPage: number;
};

export function useClientPagination<
  T extends Record<string, unknown>[] | undefined,
>({ data, itemsPerPage }: UseClientPaginationOptions<T>) {
  const { createQueryPath, updateQueryPath, queryParams } = useQueryParams([
    'page',
  ]);
  const [page, _setPage] = useState(1);
  const totalItems = data?.length ?? 0;
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const totalPagesAsArray: number[] = [];

  for (let i = 0; i < totalPages * 5; i++) {
    totalPagesAsArray.push(i + 1);
  }

  const currentPageIndex = totalPagesAsArray.indexOf(page);
  const previousPage =
    currentPageIndex > 0 ? totalPagesAsArray[currentPageIndex - 1] : undefined;
  const nextPage =
    currentPageIndex < totalPages
      ? totalPagesAsArray[currentPageIndex + 1]
      : undefined;

  const pageLimit = 5;
  const offset = currentPageIndex == 0 ? 0 : currentPageIndex == 1 ? 1 : 2;
  const offsetIndex = currentPageIndex - offset;
  const totalPagesTruncatedAsArray = totalPagesAsArray.slice(
    offsetIndex,
    offsetIndex + pageLimit,
  );

  const setPage = useCallback(
    (value: number | undefined) => {
      updateQueryPath({
        page: typeof value === 'number' ? value.toString() : value,
      });
    },
    [updateQueryPath],
  );

  useEffect(() => {
    _setPage(() => parseInt(queryParams.page ?? '1') || 1);
  }, [queryParams.page]);

  const pageItems = useMemo(() => {
    const startIndex = Math.max(0, (page - 1) * itemsPerPage);
    const endIndex = startIndex + itemsPerPage;
    return data?.slice(startIndex, endIndex) as T;
  }, [data, itemsPerPage, page]);

  return {
    createPageQueryPath: createQueryPath,
    page,
    previousPage,
    nextPage,
    pageItems,
    setPage,
    totalItems,
    totalPages,
    totalPagesAsArray,
    totalPagesTruncatedAsArray,
  };
}
