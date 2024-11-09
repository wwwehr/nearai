'use client';

import {
  Badge,
  Button,
  Card,
  Flex,
  Section,
  SvgIcon,
  Text,
} from '@near-pagoda/ui';
import { ArrowRight, Calendar } from '@phosphor-icons/react';
import React from 'react';

const ModelTimeline = () => {
  const timelineData = [
    {
      size: '0.5B',
      segments: 23,
      status: 'active',
      offset: 0,
    },
    {
      size: '2B',
      segments: 17,
      status: 'upcoming',
      offset: 40, // Starting with a small offset
    },
    {
      size: '7B',
      segments: 13,
      status: 'planned',
      offset: 80,
    },
    {
      size: '30B',
      segments: 9,
      status: 'planned',
      offset: 120,
    },
    {
      size: '70B',
      segments: 7,
      status: 'planned',
      offset: 160,
    },
    {
      size: '350B',
      segments: 4,
      status: 'planned',
      offset: 200,
    },
    {
      size: '1.4T',
      segments: 2,
      status: 'planned',
      offset: 240,
    },
  ];

  return (
    // <Card padding="m">
    <Flex direction="column" gap="s">
      <Text weight="500" size="text-s">
        Training Cadence
      </Text>
      <div style={{ overflowX: 'auto' }}>
        <div style={{ minWidth: '600px' }}>
          {timelineData.map((model) => (
            <Flex
              key={model.size}
              align="center"
              gap="m"
              style={{
                minHeight: '24px',
                opacity: model.status === 'planned' ? 0.7 : 1,
              }}
            >
              <div style={{ width: '60px' }}>
                <Text size="text-xs" weight="500">
                  {model.size}
                </Text>
              </div>

              <div style={{ flex: 1, position: 'relative' }}>
                <Flex
                  gap="s"
                  style={{
                    position: 'absolute',
                    left: model.offset,
                    right: 0,
                  }}
                >
                  {Array.from({ length: model.segments }).map((_, i) => (
                    <div
                      key={i}
                      style={{
                        flex: 1,
                        height: '6px',
                        background:
                          model.status === 'active' && i === 0
                            ? 'var(--violet-7)'
                            : 'var(--sand-8)',
                        borderRadius: '1px',
                      }}
                    />
                  ))}
                </Flex>
              </div>
            </Flex>
          ))}
        </div>
      </div>
    </Flex>
    // </Card>
  );
};

// Main component with both the model cards and timeline
const ModelTrainingSeries = () => {
  const models = [
    {
      size: '0.5B',
      status: 'active',
    },
    {
      size: '2B',
      status: 'upcoming',
      startDate: 'Q1 2025',
    },
    {
      size: '7B',
      status: 'planned',
    },
    {
      size: '30B',
      status: 'planned',
    },
    {
      size: '70B',
      status: 'planned',
    },
    {
      size: '350B',
      status: 'planned',
    },
    {
      size: '1.4T',
      status: 'planned',
    },
  ];

  const activeSeries = (
    <Card padding="l" className="mb-12">
      <Flex direction="column" gap="m">
        <Flex align="center" gap="s">
          <Text size="text-l" weight="600">
            0.5B Parameter Model
          </Text>
          <Badge variant="success" label="Active" />
        </Flex>

        <Flex direction="column" gap="s">
          <Flex align="center" gap="s">
            <SvgIcon
              icon={<Calendar weight="duotone" />}
              color="violet-9"
              size="s"
            />
            <Text>Monthly Rounds</Text>
          </Flex>
          <Text color="sand-11">
            Current round ends <b>Nov 30 @ 11:59 PM UTC</b>
          </Text>
        </Flex>

        <Button
          label="View Leaderboard"
          variant="primary"
          href="/competitions/0.5b-november-2024"
          iconRight={<ArrowRight weight="bold" />}
        />
      </Flex>
    </Card>
  );

  return (
    <Section>
      <Flex direction="column" gap="l">
        <Flex direction="column" gap="m">
          <Text as="h2" size="text-2xl" weight="600">
            Model Training Series
          </Text>
          <Text color="sand-11" size="text-l">
            A progression of increasingly capable models, with parallel
            competitions
          </Text>
        </Flex>

        {activeSeries}
        {/* Model progression */}
        <Card>
          <Flex direction="column" gap="m">
            <Text weight="600" size="text-l">
              Model Size Progression
            </Text>

            <div style={{ overflowX: 'auto', paddingBottom: '1rem' }}>
              <div style={{ minWidth: '800px' }}>
                <Flex gap="m" align="stretch">
                  {models.map((model, index) => (
                    <div
                      key={model.size}
                      style={{
                        flex: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'stretch',
                        position: 'relative',
                      }}
                    >
                      {/* Connector line */}
                      {index < models.length - 1 && (
                        <div
                          style={{
                            position: 'absolute',
                            top: '50%',
                            right: '-1rem',
                            width: '2rem',
                            height: '2px',
                            background: 'var(--sand-6)',
                            zIndex: 0,
                          }}
                        />
                      )}

                      {/* Model card */}
                      <Card
                        padding="m"
                        background={
                          model.status === 'active' ? 'violet-3' : undefined
                        }
                        style={{
                          flex: 1,
                          position: 'relative',
                          zIndex: 1,
                          opacity: model.status === 'planned' ? 0.7 : 1,
                        }}
                      >
                        <Flex direction="column" align="center" gap="s">
                          <Text
                            size="text-xl"
                            weight="600"
                            color={
                              model.status === 'planned' ? 'sand-11' : undefined
                            }
                          >
                            {model.size}
                          </Text>

                          {model.status === 'active' && (
                            <Badge variant="success" label="Active" />
                          )}
                          {model.status === 'upcoming' && (
                            <Badge variant="neutral" label={model.startDate} />
                          )}
                          {model.status === 'planned' && (
                            <Badge variant="neutral-alpha" label="Planned" />
                          )}

                          {model.status === 'active' && (
                            <Button
                              size="small"
                              variant={
                                model.status === 'active'
                                  ? 'primary'
                                  : 'secondary'
                              }
                              label={
                                model.status === 'active' ? 'View' : 'Notify Me'
                              }
                              href="/competitions/0.5b-november-2024"
                              disabled={model.status !== 'active'}
                            />
                          )}
                        </Flex>
                      </Card>
                    </div>
                  ))}
                </Flex>
              </div>
            </div>
          </Flex>
          <ModelTimeline />
        </Card>
      </Flex>
    </Section>
  );
};

export default ModelTrainingSeries;
