'use client';

import { Container } from './lib/Container';
import { Flex } from './lib/Flex';
import { Text } from './lib/Text';

const styles = {
  iconContainer: {
    maxWidth: '38px',
    maxHeight: '38px',
    borderRadius: '100%',
    overflow: 'hidden',
    flexShrink: 0,
    background: '#fff',
    boxShadow: 'var(--shadow-card-with-outline)',
    padding: '6px',
  },
  icon: {
    display: 'block',
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
};

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
  return (
    <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
      <Flex direction="column" gap="m" align="center">
        {details?.icon && (
          <div style={styles.iconContainer}>
            <img style={styles.icon} src={details.icon} alt={'Agent'} />
          </div>
        )}
        <Text size="text-l">{details?.agent?.welcome?.title}</Text>
        <Text>{details?.agent?.welcome?.description}</Text>
      </Flex>
    </Container>
  );
};
