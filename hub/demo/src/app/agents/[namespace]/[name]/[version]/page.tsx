'use client';

import { EntryEvaluationsTable } from '~/components/EntryEvaluationsTable';
import { Badge } from '~/components/lib/Badge';
import { Flex } from '~/components/lib/Flex';
import { Section } from '~/components/lib/Section';
import { Text } from '~/components/lib/Text';
import { useCurrentEntry } from '~/hooks/entries';

export default function AgentDetailsPage() {
  const { currentEntry } = useCurrentEntry('agent');

  if (!currentEntry) return null;

  return (
    <>
      <Section>
        <Text size="text-l">Description</Text>

        <Text>{currentEntry.description || 'No description provided.'}</Text>

        {currentEntry.tags.length > 0 && (
          <Flex gap="s" wrap="wrap">
            {currentEntry.tags.map((tag) => (
              <Badge label={tag} variant="neutral" key={tag} />
            ))}
          </Flex>
        )}
      </Section>

      <Section>
        <EntryEvaluationsTable entry={currentEntry} />
      </Section>
    </>
  );
}
