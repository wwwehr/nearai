import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

export function useQueryParams<const T extends string[]>(
  names: T,
  options?: {
    persistNames?: T[number][];
  },
) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const persistKey = `useQueryParams-${pathname}`;
  const [hasRestoredPersistance, setHasRestoredPersistance] = useState(false);

  const createQueryPath = useCallback(
    (updatedParams: Partial<Record<T[number], string | undefined>>) => {
      const params = new URLSearchParams(searchParams.toString());

      Object.entries(updatedParams).forEach(([name, value]) => {
        if (typeof value === 'string' && value) {
          params.set(name, value);
        } else {
          params.delete(name);
        }
      });

      return `${pathname}?${params.toString()}`;
    },
    [pathname, searchParams],
  );

  const updateQueryPath = useCallback(
    (
      updatedParams: Partial<Record<T[number], string | undefined>>,
      mode: 'push' | 'replace' = 'push',
    ) => {
      const path = createQueryPath(updatedParams);

      if (mode === 'replace') {
        router.replace(path);
      } else {
        router.push(path);
      }
    },
    [createQueryPath, router],
  );

  const queryParams = useMemo(() => {
    const params: Record<string, string> = {};

    names.forEach((name) => {
      const value = searchParams.get(name);
      if (value) {
        params[name] = value;
      }
    });

    return params as Partial<Record<T[number], string>>;

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    try {
      if (options?.persistNames) {
        const persistedQueryParams = JSON.parse(
          localStorage.getItem(persistKey) ?? '{}',
        ) as Partial<Record<T[number], string>>;

        updateQueryPath(
          {
            ...persistedQueryParams,
            ...queryParams,
          },
          'replace',
        );
      }
    } catch (error) {
      localStorage.removeItem(persistKey);
      console.error(error);
    }

    setHasRestoredPersistance(true);

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateQueryPath]);

  useEffect(() => {
    if (options?.persistNames && hasRestoredPersistance) {
      console.log('set');
      localStorage.setItem(persistKey, JSON.stringify(queryParams));
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryParams]);

  return {
    createQueryPath,
    queryParams,
    updateQueryPath,
  };
}
