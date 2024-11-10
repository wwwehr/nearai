'use client';

import CompetitionPage from '~/app/competitions/[competition]/CompetitionPage';
import { Markdown } from '~/components/lib/Markdown';

export default function ModelTrainingPage() {
  const content = `
Welcome to the first NEAR AI competition.

In this competition, we want the participants to pre-train a 0.5B parameter model that performs as well as possible on a versatile benchmark called [LiveBench](https://livebench.ai/).

0.5B parameter model is quite small in the model world, but it can be trained relatively quickly, and thus allows iterating over various ideas and techniques. We will host more competition for large models, and scaling laws, in the new future. Learn more about this strategy [on the NEAR AI blog](https://near.ai).

To participate, you will need \`nearai-cli\` installed on your computer. For details and documentation, visit the [nearai-cli GitHub page](https://github.com/nearai/nearai).

From your machine you will use \`nearai-cli submit\` to submit your runs. From within the run, you will use \`near-cli\` to download raw data and to upload datasets and pre-trained models, as well as to run evaluations.

Whenever you run a LiveBench benchmark from a run initiated with \`nearai-cli submit\`, the result will appear on the leaderboard.
`;
  return (
    <CompetitionPage title="0.5B Model Training Competition - November 2024">
      <Markdown content={content} />
    </CompetitionPage>
  );
}
