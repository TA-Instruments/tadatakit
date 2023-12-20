import re


def pascal_to_snake(name: str) -> str:
    """
    Convert a PascalCase string to a snake_case string.

    Args:
        name (str): The PascalCase string to convert.

    Returns:
        str: The converted snake_case string.
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_pascal(name: str) -> str:
    """
    Convert a snake_case string to a PascalCase string.

    Args:
        name (str): The snake_case string to convert.

    Returns:
        str: The converted PascalCase string.
    """
    return "".join(x.title() for x in name.split("_"))
