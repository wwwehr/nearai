import { promises as fs } from 'fs';
import path from 'path';
import { type z } from 'zod';

import { entryModel } from '~/lib/models';

const entryMetadata = entryModel.partial();
type EntryMetadata = z.infer<typeof entryMetadata>;
export async function readMetadataJson(
  filePath: string,
): Promise<EntryMetadata | null> {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    return entryMetadata.parse(JSON.parse(data));
  } catch (err) {
    console.error(`Error reading ${filePath}`);
    return null;
  }
}
export async function processDirectory(
  dirPath: string,
  results: EntryMetadata[],
  registryPath: string,
): Promise<EntryMetadata[]> {
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
            const metadata: EntryMetadata | null =
              await readMetadataJson(filePath);
            if (metadata) {
              metadata.id = results.length + 1;

              const agentRelativePath = path.relative(registryPath, dirPath);
              const agentPathParts = agentRelativePath.split(path.sep);
              if (
                agentPathParts.length > 0 &&
                agentPathParts[0]?.endsWith('.near')
              ) {
                // ignore version from metadata if actual version in filePath is different
                metadata.version = agentPathParts[agentPathParts.length - 1];

                metadata.namespace = agentPathParts[0];
                results.push(metadata);
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
