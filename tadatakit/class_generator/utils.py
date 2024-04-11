import re
import datetime
from typing import Tuple, Dict, Any
from types import FunctionType


def pascal_to_snake(name: str) -> str:
    """
    Converts a PascalCase string to a snake_case string.

    This function takes a string formatted in PascalCase and converts it to snake_case.
    It handles compound words by inserting underscores between words, where each word starts
    with a capital letter in the original string. If the input string is not a valid identifier,
    it returns the string unchanged.

    Args:
        name (str): The PascalCase string to convert.

    Returns:
        str: The converted snake_case string, or the original string if it is not a valid identifier.
    """
    if not name.isidentifier():
        return name
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_pascal(name: str) -> str:
    """
    Converts a snake_case string to a PascalCase string.

    This function takes a string formatted in snake_case and converts it to PascalCase by
    capitalizing the first letter of each word and removing underscores. If the input string
    is not a valid identifier, it returns the string unchanged.

    Args:
        name (str): The snake_case string to convert.

    Returns:
        str: The converted PascalCase string, or the original string if it is not a valid identifier.
    """
    if not name.isidentifier():
        return name
    return "".join(x.title() for x in name.split("_"))


def json_serializer(obj: Any) -> str:
    """
    JSON serializer for objects not serializable by default json code.

    Args:
        obj (Any): The object to be serialized.

    Returns:
        str: A JSON-compliant string representation of the object.

    Raises:
        TypeError: If the object is not serializable.
    """
    if isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    raise TypeError("Type %s not serializable" % type(obj))


def split_props_by_required(definition: Dict) -> Tuple[Dict, Dict]:
    """
    Splits properties of a JSON schema definition into required and non-required.

    Args:
        definition (Dict[str, Any]): The JSON schema definition containing properties.

    Returns:
        Tuple[Dict[str, Any], Dict[str, Any]]: Two dictionaries, one with required and the other with
        non-required properties.
    """
    properties = definition.get("properties", {})
    required = set(definition.get("required", []))

    required_props = {p: properties[p] for p in properties if p in required}
    non_required_props = {p: properties[p] for p in properties if p not in required}

    return required_props, non_required_props


def copy_function(original_function: FunctionType) -> FunctionType:
    """
    Creates a copy of a given function.

    This method duplicates a function, including its code, globals, name, defaults,
    closures, and other attributes, making a full copy that behaves like the original.

    Args:
        original_function (FunctionType): The function to copy.

    Returns:
        FunctionType: A duplicate of the original function.
    """
    duplicate_function = FunctionType(
        original_function.__code__,
        original_function.__globals__,
        original_function.__name__,
        original_function.__defaults__,
        original_function.__closure__,
    )
    duplicate_function.__dict__.update(original_function.__dict__)
    duplicate_function.__annotations__.update(original_function.__annotations__)
    return duplicate_function
