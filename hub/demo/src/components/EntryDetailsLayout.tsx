'use client';

import { CaretDown } from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { type ReactElement, type ReactNode } from 'react';

import { ErrorSection } from '~/components/ErrorSection';
import { Badge } from '~/components/lib/Badge';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { ImageIcon } from '~/components/lib/ImageIcon';
import { PlaceholderSection } from '~/components/lib/Placeholder';
import { Section } from '~/components/lib/Section';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Tabs } from '~/components/lib/Tabs';
import { Text } from '~/components/lib/Text';
import { StarButton } from '~/components/StarButton';
import { useCurrentEntry, useEntryParams } from '~/hooks/entries';
import { ENTRY_CATEGORY_LABELS } from '~/lib/entries';
import { type EntryCategory } from '~/lib/models';

type Props = {
  category: EntryCategory;
  children: ReactNode;
  tabs: {
    path: string;
    label: string;
    icon: ReactElement;
  }[];
};

export const EntryDetailsLayout = ({ category, children, tabs }: Props) => {
  const pathname = usePathname();
  const { namespace, name, version } = useEntryParams();
  const { currentEntry, currentEntryIsHidden, currentVersions } =
    useCurrentEntry(category);
  const baseUrl = `/${category}s/${namespace}/${name}`;
  const activeTabPath = pathname.replace(`${baseUrl}/${version}`, '');

  if (currentEntryIsHidden) {
    return <ErrorSection error="404" />;
  }

  return (
    <>
      <Section background="sand-0" bleed gap="m" tabs>
        <Flex
          align="center"
          gap="m"
          phone={{ direction: 'column', align: 'start', gap: 'l' }}
        >
          <Flex
            align="center"
            gap="m"
            style={{ width: '100%' }}
            phone={{ justify: 'space-between' }}
          >
            <Flex align="center" gap="m">
              <ImageIcon
                size="l"
                src={currentEntry?.details.icon}
                alt={name}
                fallbackIcon={ENTRY_CATEGORY_LABELS[category].icon}
              />

              <Flex gap="none" direction="column" align="start">
                <Flex align="center" gap="m">
                  <Link href={baseUrl}>
                    <Text as="h1" size="text-l" weight={600} color="sand-12">
                      {name}
                    </Text>
                  </Link>

                  <Dropdown.Root>
                    <Dropdown.Trigger asChild>
                      <Badge
                        button
                        label={version}
                        iconRight={<CaretDown />}
                        variant="neutral"
                      />
                    </Dropdown.Trigger>

                    <Dropdown.Content>
                      <Dropdown.Section>
                        <Dropdown.SectionContent>
                          <Text size="text-xs" weight={600} uppercase>
                            Versions
                          </Text>
                        </Dropdown.SectionContent>

                        {currentVersions?.map((entry) => (
                          <Dropdown.Item
                            href={`${baseUrl}/${entry.version}`}
                            key={entry.version}
                          >
                            {entry.version}
                          </Dropdown.Item>
                        ))}
                      </Dropdown.Section>
                    </Dropdown.Content>
                  </Dropdown.Root>
                </Flex>

                <Link
                  href={`/profiles/${namespace}`}
                  style={{ marginTop: '-0.1rem' }}
                >
                  <Text size="text-s" weight={500}>
                    @{namespace}
                  </Text>
                </Link>
              </Flex>
            </Flex>
          </Flex>

          <StarButton entry={currentEntry} variant="detailed" />
        </Flex>

        <Tabs.Root value={activeTabPath}>
          <Tabs.List>
            {tabs.map((tab) => (
              <Tabs.Trigger
                href={`${baseUrl}/${version}${tab.path}`}
                value={tab.path}
                key={tab.path}
              >
                <SvgIcon icon={tab.icon} />
                {tab.label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
        </Tabs.Root>
      </Section>

      {!currentEntry && <PlaceholderSection />}

      {children}
    </>
  );
};
