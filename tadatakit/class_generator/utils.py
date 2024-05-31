from typing import Type, Any, get_origin, get_args, Union, Dict, Tuple, Optional
from types import FunctionType
import re
import datetime
import uuid


def type_hint_to_str(type_hint: Type) -> str:
    """
    Get a string representation of a type hint.

    Args:
        type_hint (Type): The type hint to convert to a string.

    Returns:
        str: A string representation of the type hint.
    """
    try:
        return type_hint.__name__
    except AttributeError:
        return (
            type_hint.__str__()
            .replace("typing.", "")
            .replace("tadatakit.class_generator.definition_registry.", "")
        )


def is_instance(obj: Any, type_hint: Type) -> bool:
    """
    Custom type check that understands typing module constructs, such as Union and List.

    Args:
        obj (Any): The object to check.
        type_hint (Type): The type hint against which the object is to be checked.

    Returns:
        bool: True if obj is an instance of type_hint, False otherwise.

    Raises:
        TypeError: If there is an issue with the type hint or the object during type checking.
    """
    try:
        if type_hint is Any:
            return True
        if get_origin(type_hint) is Union:
            return any(is_instance(obj, arg) for arg in get_args(type_hint))
        elif get_origin(type_hint) is list and isinstance(obj, list):
            element_type = get_args(type_hint)[0]
            return all(isinstance(elem, element_type) for elem in obj)
        elif isinstance(obj, type_hint):
            return True
        return False
    except TypeError as e:
        raise TypeError(f"type_hint: {type_hint}, obj: {obj}") from e


def pascal_to_snake(name: str, special_names_set: set) -> str:
    """
    Converts a PascalCase string to a snake_case string.

    This function takes a string formatted in PascalCase and converts it to snake_case.
    It handles compound words by inserting underscores between words, where each word starts
    with a capital letter in the original string. If the input string is not a valid identifier,
    it returns the string unchanged.

    Args:
        name (str): The PascalCase string to convert.
        special_names_set (set): a set of special names which should not be converted

    Returns:
        str: The converted snake_case string, or the original string if it is not a valid identifier.
    """
    if not name.isidentifier():
        return name
    elif "_" in name:
        special_names_set.add(name)
        return name
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_pascal(name: str, special_names_set: set) -> str:
    """
    Converts a snake_case string to a PascalCase string.

    This function takes a string formatted in snake_case and converts it to PascalCase by
    capitalizing the first letter of each word and removing underscores. If the input string
    is not a valid identifier, it returns the string unchanged.

    Args:
        name (str): The snake_case string to convert.
        special_names_set (set): a set of special names which should not be converted

    Returns:
        str: The converted PascalCase string, or the original string if it is not a valid identifier.
    """
    if not name.isidentifier():
        return name
    elif name in special_names_set:
        return name
    return "".join(x.title() for x in name.split("_"))


def pascal_to_screaming_snake(
    name: str, special_names_set: Optional[set] = None
) -> str:
    """
    Converts a PascalCase string to a SCREAMING_SNAKE_CASE string.

    This function takes a string formatted in PascalCase and converts it to SCREAMING_SNAKE_CASE.
    It handles compound words by inserting underscores between words, where each word starts
    with a capital letter in the original string. If the input string is not a valid identifier,
    it returns the string unchanged.

    Args:
        name (str): The PascalCase string to convert.
        special_names_set (Optional[set]): a set of special names which should not be converted

    Returns:
        str: The converted SCREAMING_SNAKE_CASE string, or the original string if it is not a
             valid identifier.
    """
    if special_names_set is None:
        special_names_set = set()
    if not name.isidentifier():
        return name
    elif "_" in name:
        special_names_set.add(name)
        return name
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).upper()


def screaming_snake_to_pascal(
    name: str, special_names_set: Optional[set] = None
) -> str:
    """
    Converts a SCREAMING_SNAKE_CASE string to a PascalCase string.

    This function takes a string formatted in SCREAMING_SNAKE_CASE and converts it to PascalCase by
    capitalizing the first letter of each word and removing underscores. If the input string
    is not a valid identifier, it returns the string unchanged.

    Args:
        name (str): The SCREAMING_SNAKE_CASE string to convert.
        special_names_set (Optional[set]): a set of special names which should not be converted

    Returns:
        str: The converted PascalCase string, or the original string if it is not a valid identifier.
    """
    if special_names_set is None:
        special_names_set = set()
    if not name.isidentifier():
        return name
    elif name in special_names_set:
        return name
    return "".join(x.title() for x in name.split("_"))


def convert_non_json_serializable_types(obj: Any) -> str:
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
    elif isinstance(obj, uuid.UUID):
        return str(obj)
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
