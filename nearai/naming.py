import re


def get_canonical_name(name: str) -> str:
    """Returns a name that can be used for matching entities.

    Applies such transformations:
    1. All letters lowercase.
    2. Convert '.' between digits to 'p'.
    3. Convert '<not letter>v<digit>' -> '<not letter><digit>'
    4. Remove all non-alphanumeric characters except between digits.
        Use '_' between digits.
    5. Convert 'metallama' -> 'llama'.

    e.g. "llama-3.1-70b-instruct" -> "llama3p1_70binstruct"
    """
    # Convert to lowercase
    name = name.lower()
    # Convert '.' between digits to 'p'
    name = re.sub(r"(\d)\.(\d)", r"\1p\2", name)
    # Convert '<digit>v<digit>' -> '<digit>_<digit>'
    name = re.sub(r"(\d)v(\d)", r"\1_\2", name)
    # Convert '<not letter>v<digit>' -> '<not letter><digit>'
    name = re.sub(r"(^|[^a-z])v(\d)", r"\1\2", name)
    # Replace non-alphanumeric characters between digits with '_'
    name = re.sub(r"(\d)[^a-z0-9]+(\d)", r"\1_\2", name)
    # Remove remaining non-alphanumeric characters, except '_'
    name = re.sub(r"[^a-z0-9_]", "", name)
    # Remove any remaining underscores that are not between digits
    name = re.sub(r"(?<!\d)_|_(?!\d)", "", name)
    # Convert 'metallama' to 'llama'
    name = name.replace("metallama", "llama")
    return name
