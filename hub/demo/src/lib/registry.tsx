import {
  ChartBar,
  Database,
  GraduationCap,
  Graph,
  Lightbulb,
  TerminalWindow,
} from '@phosphor-icons/react';
import { type ReactElement } from 'react';
import { type z } from 'zod';

import { type RegistryCategory } from '~/server/api/routers/hub';

import { type registryEntryModel } from './models';

export const REGISTRY_CATEGORY_LABELS: Record<
  // eslint-disable-next-line @typescript-eslint/ban-types
  RegistryCategory | (string & {}),
  {
    icon: ReactElement;
    label: string;
  }
> = {
  agent: {
    icon: <Lightbulb />,
    label: 'Agent',
  },
  benchmark: {
    icon: <GraduationCap />,
    label: 'Benchmark',
  },
  dataset: {
    icon: <Database />,
    label: 'Dataset',
  },
  environment: {
    icon: <TerminalWindow />,
    label: 'Environment',
  },
  evaluation: {
    icon: <ChartBar />,
    label: 'Evaluation',
  },
  model: {
    icon: <Graph />,
    label: 'Model',
  },
};

export function primaryUrlForRegistryItem(
  item: z.infer<typeof registryEntryModel>,
) {
  let url: string | undefined;

  switch (item.category as RegistryCategory) {
    case 'agent':
      url = `/agents/${item.namespace}/${item.name}/${item.version}`;
      break;

    case 'benchmark':
      url = benchmarkEvaluationsUrlForRegistryItem(item);
      break;
  }

  return url;
}

export function benchmarkEvaluationsUrlForRegistryItem(
  item: z.infer<typeof registryEntryModel>,
) {
  let url: string | undefined;

  switch (item.category as RegistryCategory) {
    case 'agent':
      url = `/evaluations?search=${encodeURIComponent(`${item.namespace}/${item.name}`)}`;
      break;

    case 'benchmark':
      url = `/evaluations?benchmarks=${item.id}`;
      break;

    case 'model':
      url = `/evaluations?search=${encodeURIComponent(`${item.name}`)}`;
      break;
  }

  return url;
}
