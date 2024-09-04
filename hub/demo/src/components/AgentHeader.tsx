'use client';

import styles from './AgentHeader.module.css';
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
  return (
    <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
      <Flex direction="column" gap="m" align="center">
        {details?.icon && (
          <div className={styles.icon}>
            <img src={details.icon} alt={'Agent'} />
          </div>
        )}
        <Text size="text-l">{details?.agent?.welcome?.title}</Text>
        <Text>{details?.agent?.welcome?.description}</Text>
      </Flex>
    </Container>
  );
};
