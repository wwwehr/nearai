'use client';

import { useTheme } from 'next-themes';

import { Container } from './lib/Container';
import { Flex } from './lib/Flex';
import { Text } from './lib/Text';

interface AgentHeaderProps {
  details?: {
    icon?: string;
    agent?: {
      welcome?: {
        title?: string;
        description?: string;
      };
    };
  };
}

export const AgentHeader = ({ details }: AgentHeaderProps) => {
  const { resolvedTheme, _ } = useTheme();

  const styles = {
    icon: {
      maxWidth: '32px',
      maxHeight: '32px',
      filter: resolvedTheme === 'dark' ? 'invert(1)' : 'none',
    },
  };

  return (
    <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
      <Flex direction="column" gap="m" align="center">
        {details?.icon && (
          <img src={details?.icon} style={styles.icon} alt={'Agent'} />
        )}
        <Text size="text-l">{details?.agent?.welcome?.title}</Text>
        <Text>{details?.agent?.welcome?.description}</Text>
      </Flex>
    </Container>
  );
};
