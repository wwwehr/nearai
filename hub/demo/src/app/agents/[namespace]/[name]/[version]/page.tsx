'use client';

import { Badge } from '~/components/lib/Badge';
import { Flex } from '~/components/lib/Flex';
import { Section } from '~/components/lib/Section';
import { Text } from '~/components/lib/Text';
import { useCurrentEntry } from '~/hooks/entries';

/*
  TODO:

  - Add evaluation summary table to agent details summary page (with CTA to view evaluations page)
  - Come up with solution for sticky table header since position sticky won't be an option anymore
*/

export default function AgentDetailsPage() {
  const { currentEntry } = useCurrentEntry('agent');

  if (!currentEntry) return null;

  return (
    <>
      <Section>
        <Text>{currentEntry.description}</Text>

        <Flex gap="s" wrap="wrap">
          {currentEntry.tags.map((tag) => (
            <Badge label={tag} variant="neutral" key={tag} />
          ))}
        </Flex>
      </Section>
    </>
  );
}
