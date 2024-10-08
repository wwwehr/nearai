import { promises as fs } from 'fs';
import path from 'path';
import { type z } from 'zod';

import { type entryModel, metadataModel } from '~/lib/models';

type EntryModel = z.infer<typeof entryModel>;
type MetadataModel = z.infer<typeof metadataModel>;

function transformMetadataToEntry(
  metadata: z.infer<typeof metadataModel>,
): z.infer<typeof entryModel> {
  return {
    id: 0,
    category: metadata.category,
    namespace: 'undefined',
    name: metadata.name,
    version: metadata.version,
    description: metadata.description,
    tags: metadata.tags,
    show_entry: metadata.show_entry,
    starred_by_point_of_view: false,
    num_stars: 0,
    details: metadata.details,
  };
}

export async function readMetadataJson(
  filePath: string,
): Promise<MetadataModel | null> {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    return metadataModel.parse(JSON.parse(data));
  } catch (err) {
    console.error(`Error reading ${filePath}`);
    return null;
  }
}

export async function processDirectory(
  dirPath: string,
  results: EntryModel[],
  registryPath: string,
): Promise<EntryModel[]> {
  try {
    const files = await fs.readdir(dirPath, { withFileTypes: true });

    await Promise.all(
      files.map(async (file) => {
        // skip hidden items
        if (file.name.startsWith('.')) return;

        const filePath = path.join(dirPath, file.name);
        if (file.isDirectory()) {
          await processDirectory(filePath, results, registryPath);
        } else if (file.name === 'metadata.json') {
          try {
            const metadata: MetadataModel | null =
              await readMetadataJson(filePath);
            if (metadata) {
              const entry = transformMetadataToEntry(metadata);
              entry.id = results.length + 1;

              const agentRelativePath = path.relative(registryPath, dirPath);
              const agentPathParts = agentRelativePath.split(path.sep);
              if (
                agentPathParts.length > 0 &&
                agentPathParts[0]?.endsWith('.near')
              ) {
                // ignore version from metadata if actual version in filePath is different
                entry.version = agentPathParts[agentPathParts.length - 1] ?? '';
                entry.namespace = agentPathParts[0];
                results.push(entry);
              }
            }
          } catch (err) {
            // Ignore error if agent.py doesn't exist or any other read error
          }
        }
      }),
    );
  } catch (err) {
    console.error(`Error reading ${dirPath}`);
  }

  return results;
}
