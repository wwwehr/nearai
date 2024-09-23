export function wordsMatchFuzzySearch(words: string[], search: string) {
  const normalizedWords = words.map((word) =>
    word.toLowerCase().replace(/[^a-zA-Z0-9]/g, ''),
  );
  const normalizedSearchWords = search
    .split(/[-_\s]/)
    .map((word) => word.toLowerCase().replace(/[^a-zA-Z0-9]/g, ''));

  const matches = normalizedSearchWords.every((searchWord) =>
    normalizedWords.find((itemWord) => itemWord.indexOf(searchWord) > -1),
  );

  return matches;
}
