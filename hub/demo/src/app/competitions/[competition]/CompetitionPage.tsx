'use client';

import React from 'react';
import { Section, Text } from '@near-pagoda/ui';
import { EvaluationsTable } from '~/components/EvaluationsTable';
import type { z } from 'zod';
import type { entryModel } from '~/lib/models';

const CompetitionPage = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => {
  const benchmarkEntry: z.infer<typeof entryModel> | undefined = undefined; // TODO
  const initialBenchmarkColumns: string[] | undefined = undefined; // TODO

  return (
    <>
      <Section>
        <Text as="h1" size="text-3xl" weight="600" className="mb-12">
          {title}
        </Text>
        {children}
      </Section>

      <Section>
        <EvaluationsTable
          title="Leaderboard"
          entry={benchmarkEntry}
          initialBenchmarkColumns={initialBenchmarkColumns}
        />
      </Section>
    </>
  );
};

export default CompetitionPage;
