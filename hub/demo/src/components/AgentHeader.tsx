'use client';

import { Container } from './lib/Container';
import { Flex } from './lib/Flex';
import { Text } from './lib/Text';

const styles = {
  icon: {
    maxWidth: '32px',
    maxHeight: '32px',
  },
};

interface AgentHeaderProps {
  details?: {
    agent?: {
      icon?: string;
      title?: string;
      welcome_message?: string;
    };
  };
}

export const AgentHeader = ({ details }: AgentHeaderProps) => {
  return (
    <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
      <Flex direction="column" gap="m" align="center">
        {details?.agent?.icon && (
          <img src={details?.agent?.icon} style={styles.icon} alt={'Agent'} />
        )}
        <Text size="text-l">{details?.agent?.title}</Text>
        <Text>{details?.agent?.welcome_message}</Text>
      </Flex>
    </Container>
  );
};
