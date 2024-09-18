'use client';

import { CodeBlock, Play } from '@phosphor-icons/react';
import { type ReactNode } from 'react';
import { type z } from 'zod';

import { Badge } from '~/components/lib/Badge';
import { Button } from '~/components/lib/Button';
import { Card } from '~/components/lib/Card';
import { Flex } from '~/components/lib/Flex';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { StarButton } from '~/components/StarButton';
import { type registryEntryModel } from '~/lib/models';
import {
  primaryUrlForRegistryItem,
  REGISTRY_CATEGORY_LABELS,
} from '~/lib/registry';

import { ConditionalLink } from './lib/ConditionalLink';
import { ImageIcon } from './lib/ImageIcon';

type Props = {
  item: z.infer<typeof registryEntryModel>;
  linksOpenNewTab?: boolean;
  footer?: ReactNode;
};

export const ResourceCard = ({ item, linksOpenNewTab, footer }: Props) => {
  const icon = REGISTRY_CATEGORY_LABELS[item.category]?.icon;
  const primaryUrl = primaryUrlForRegistryItem(item);
  const target = linksOpenNewTab ? '_blank' : undefined;

  return (
    <Card gap="m">
      <Flex gap="s" align="center">
        <ConditionalLink href={primaryUrl}>
          <ImageIcon
            src={item.details.icon}
            alt={item.name}
            fallbackIcon={icon}
          />
        </ConditionalLink>

        <Flex gap="none" direction="column">
          <ConditionalLink
            href={primaryUrl}
            target={target}
            style={{ zIndex: 1, position: 'relative' }}
          >
            <Text size="text-base" weight={600} color="sand-12">
              {item.name}
            </Text>
          </ConditionalLink>

          <ConditionalLink
            href={`/profiles/${item.namespace}`}
            target={target}
            style={{ marginTop: '-0.1rem' }}
          >
            <Text size="text-xs" weight={400}>
              @{item.namespace}
            </Text>
          </ConditionalLink>
        </Flex>
      </Flex>

      {item.description && <Text size="text-s">{item.description}</Text>}

      <Flex gap="s" align="center">
        <Badge
          label={
            REGISTRY_CATEGORY_LABELS[item.category]?.label ?? item.category
          }
          variant="neutral"
        />

        <Tooltip content="Latest Version">
          <Badge label={item.version} variant="neutral" />
        </Tooltip>

        <StarButton item={item} variant="simple" />

        {item.category === 'agent' && (
          <>
            <Tooltip asChild content="View Source">
              <Button
                label="View Source"
                icon={<CodeBlock weight="duotone" />}
                size="small"
                fill="ghost"
                target={target}
                href={`${primaryUrl}/source`}
              />
            </Tooltip>

            <Tooltip asChild content="Run Agent">
              <Button
                label="Run"
                icon={<Play weight="duotone" />}
                size="small"
                fill="ghost"
                target={target}
                href={`${primaryUrl}/run`}
              />
            </Tooltip>
          </>
        )}
      </Flex>

      {footer}
    </Card>
  );
};
