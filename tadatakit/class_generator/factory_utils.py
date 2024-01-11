import json
import datetime
import uuid
from typing import Dict, Tuple, List, Type, Optional, Union, get_origin, get_args

from .schema_object import SchemaObject


def load_schema(file_path: str) -> Dict:
    """
    Load and return the JSON schema from a specified file path.

    Args:
        file_path (str): The file path to the JSON schema file.

    Returns:
        dict: The loaded JSON schema as a dictionary.
    """
    with open(file_path) as file:
        return json.load(file)


def register_classes_in_globals(globals_dict: Dict, class_registry: Dict):
    """
    Register classes in the global namespace.

    This function takes each class from the class registry and adds it
    to the global namespace, allowing these classes to be imported
    from the `class_generator` module

    Args:
        globals_dict (Dict): The global namespace dictionary.
        class_registry (Dict): The registry of classes to be registered.

    Returns:
        None
    """
    for class_name, class_dict in class_registry.items():
        globals_dict[class_name] = class_dict["class"]


def get_ref(schema: Dict, ref_str: str) -> Dict:
    """
    Retrieve a specific part of the schema based on the JSON pointer reference.

    Args:
        schema (Dict): The JSON schema in which to look for the reference.
        ref_str (str): The JSON pointer reference string.

    Returns:
        Dict: The part of the schema referenced by ref_str.
    """
    json_path = ref_str.split("/")[1:]
    level = schema
    for key in json_path:
        level = level[key]
    return level


def get_ref_path(schema: Dict, ref_path: str) -> Dict:
    """
    Navigate the schema to find a specific $ref path.

    Args:
        schema (Dict): The JSON schema to navigate.
        ref_path (str): The path to the reference in the schema.

    Returns:
        Dict: The part of the schema referenced by ref_path.
    """
    parts = ref_path.strip("#/").split("/")
    current = schema
    for part in parts:
        current = current.get(part, {})
        if not current:
            break
    return current


def find_refs(schema: Dict, refs: Optional[List[str]] = None) -> List[str]:
    """
    Recursively find all $ref references in a JSON schema.

    Args:
        schema (Dict): The JSON schema to search.
        refs (Optional[List[str]]): The list to accumulate references.

    Returns:
        List[str]: A list of all $ref references found in the schema.
    """
    if refs is None:
        refs = []

    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "$ref":
                if value not in refs:
                    refs.append(value)
                    nested_schema = get_ref_path(schema, value)
                    find_refs(nested_schema, refs)
            elif key in ["allOf", "anyOf", "oneOf"]:
                for item in value:
                    find_refs(item, refs)
            else:
                find_refs(value, refs)
    elif isinstance(schema, list):
        for item in schema:
            find_refs(item, refs)

    return refs


def split_props_by_required(subschema: dict) -> Tuple[Dict, Dict]:
    """
    Splits properties of a JSON schema subschema into required and non-required.

    Args:
        subschema (dict): The JSON schema subschema containing properties.

    Returns:
        Tuple[Dict, Dict]: Two dictionaries, one with required and the other with
        non-required properties.
    """
    properties = subschema.get("properties", {})
    required = set(subschema.get("required", []))

    required_props = {p: properties[p] for p in properties if p in required}
    non_required_props = {p: properties[p] for p in properties if p not in required}

    return required_props, non_required_props


def type_hint_generator(
    property_definition: Dict, is_optional: bool, class_registry: Dict
) -> Type:
    """
    Determines the type hint for a given property definition.

    This function maps JSON schema data types to Python data types, handling
    both basic types and references to other schema objects.

    Args:
        property_definition (Dict): The JSON schema property definition.
        is_optional (bool): Indicates if the property is optional.
        class_registry (Dict): A registry of already created class types.

    Returns:
        Type: The Python type or class that corresponds to the property definition.
    """
    type_mapping = {
        "array": list,
        "boolean": bool,
        "integer": int,
        "number": float,
        "object": object,
        "string": str,
    }

    format_mapping = {
        "date-time": datetime.datetime,
        "uuid": uuid.UUID,
        "byte": bytes,  # For base64 encoded data
    }

    if "type" in property_definition:
        type_hint = type_mapping[property_definition["type"]]

        if "format" in property_definition:
            type_hint = format_mapping.get(property_definition["format"], type_hint)

        if type_hint is list:
            if "items" in property_definition:
                subitems = type_hint_generator(
                    property_definition["items"], False, class_registry
                )
                type_hint = List[subitems]

        return Optional[type_hint] if is_optional else type_hint

    elif "$ref" in property_definition:
        class_name = property_definition["$ref"].rsplit("/", 1)[-1]
        type_hint = class_registry[class_name]["type_hint"]
        return Optional[type_hint] if is_optional else type_hint

    else:
        raise TypeError(f"Unsupported schema property: {property_definition}")


def identify_class_of_ref(subschema: Dict) -> Tuple[bool, Optional[Type]]:
    """
    Identify the class type for a given subschema reference.

    Args:
        subschema (Dict): The JSON subschema to identify the class for.

    Returns:
        Tuple[bool, Optional[Type]]: A tuple indicating whether to subclass it and the identified class type.
    """
    type_mapping = {
        "array": list,
        "boolean": bool,
        "integer": int,
        "number": float,
        "object": object,
        "string": str,
    }

    format_mapping = {
        "date-time": datetime.datetime,
        "uuid": uuid.UUID,
        "byte": bytes,  # For base64 encoded data
    }

    subclass_it = False
    if "properties" in subschema or "additionalProperties" in subschema:
        class_type = SchemaObject
        subclass_it = True
    elif "allOf" in subschema:
        class_type = SchemaObject
        subclass_it = True
    elif "anyOf" in subschema:
        class_type = None
    elif "type" in subschema:
        class_type = type_mapping[subschema["type"]]
        if "format" in subschema:
            class_type = format_mapping.get(subschema["format"], class_type)
    else:
        raise TypeError(f"Unsupported subschema: {subschema}")
    return subclass_it, class_type
