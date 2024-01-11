import json
from typing import Dict, Any, Type

from .schema_object import SchemaObject
from .factory_utils import (
    find_refs,
    get_ref,
    type_hint_generator,
    split_props_by_required,
    identify_class_of_ref,
)
from .common_utils import pascal_to_snake


def initialize_class_registry(
    schema: Dict, start_ref: str
) -> Dict[str, Dict[str, Any]]:
    """
    Initialize the class registry based on the schema and a starting reference.

    Args:
        schema (Dict): The JSON schema.
        start_ref (str): The starting reference point in the schema.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary representing the class registry.
    """
    refs = find_refs(schema, [start_ref])
    class_registry = {}
    for ref in refs:
        subschema = get_ref(schema, ref)
        class_name = ref.rsplit("/", 1)[-1]
        subclass_it, class_type = identify_class_of_ref(subschema)
        if class_type is not None:
            if subclass_it:
                new_class = type(class_name, (class_type,), {})
                new_class.__doc__ = (
                    f"A TA Instruments `{class_name}` class derived from the "
                    f"following schema:\n```\n{json.dumps(subschema, indent=4)}\n```"
                )  # TODO: add a for more information section
                new_class._doc_string_base = (
                    f"Initialize a TA Instruments `{class_name}` class.\n\nArgs:"
                )
                class_registry[class_name] = {
                    "class": new_class,
                    "subschema": subschema,
                }
            else:
                class_registry[class_name] = {
                    "class": class_type,
                    "subschema": subschema,
                }
    return class_registry


def add_type_hints(
    class_registry: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Add type hints to the classes in the class registry.

    Args:
        class_registry (Dict[str, Dict[str, Any]]): The class registry.

    Returns:
        Dict[str, Dict[str, Any]]: The updated class registry with type hints added.
    """
    for class_name, class_dict in class_registry.items():
        if class_dict["class"] is list:
            type_hint = type_hint_generator(
                class_dict["subschema"],
                is_optional=False,
                class_registry=class_registry,
            )
        else:
            type_hint = class_dict["class"]
        class_registry[class_name]["type_hint"] = type_hint
    return class_registry


def populate_classes(
    class_registry: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Populate the classes in the class registry with properties.

    Args:
        class_registry (Dict[str, Dict[str, Any]]): The class registry.

    Returns:
        Dict[str, Dict[str, Any]]: The updated class registry with populated classes.
    """
    for _, class_dict in class_registry.items():
        if issubclass(class_dict["class"], SchemaObject):
            _add_properties_to_class(class_dict, class_registry)
    return class_registry


def _add_properties_to_class(
    class_dict: Dict[str, Any], class_registry: Dict[str, Dict[str, Any]]
) -> None:
    """
    Add properties to a class based on its subschema.

    Args:
        class_dict (Dict[str, Any]): The dictionary containing class and subschema information.
    """
    required_props, non_required_props = split_props_by_required(
        class_dict["subschema"]
    )
    for prop_name, prop in required_props.items():
        _add_property_to_class(
            class_dict["class"], prop_name, prop, False, class_registry
        )
    for prop_name, prop in non_required_props.items():
        _add_property_to_class(
            class_dict["class"], prop_name, prop, True, class_registry
        )


def _add_property_to_class(
    class_obj: Type,
    prop_name: str,
    prop: Dict,
    is_optional: bool,
    class_registry: Dict[str, Dict[str, Any]],
) -> None:
    """
    Add a property to a class.

    Args:
        class_obj (Type): The class to which the property will be added.
        prop_name (str): The name of the property.
        prop (Dict): The property schema.
        is_optional (bool): Indicates whether the property is optional.
        class_registry (Dict[str, Dict[str, Any]]): The class registry.
    """
    snake_case_name = pascal_to_snake(prop_name)
    type_hint = type_hint_generator(prop, is_optional, class_registry)
    if is_optional:
        class_obj.add_property(
            snake_case_name, type_hint, description=None, default=None
        )  # TODO: Replace with actual description if available
    else:
        class_obj.add_property(
            snake_case_name, type_hint, description=None
        )  # TODO: Replace with actual description if available


def class_registry_factory(schema: Dict, start_ref: str) -> Dict[str, Dict[str, Any]]:
    """
    Factory function to create a class registry from a given schema and starting reference.

    Args:
        schema (Dict): The JSON schema.
        start_ref (str): The starting reference point in the schema.

    Returns:
        Dict[str, Dict[str, Any]]: The created class registry.
    """
    class_registry = initialize_class_registry(schema, start_ref)
    class_registry = add_type_hints(class_registry)
    class_registry = populate_classes(class_registry)
    return class_registry
