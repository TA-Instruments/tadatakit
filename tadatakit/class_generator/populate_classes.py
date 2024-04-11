from typing import Any, Type, Dict, List, Union, Optional, Tuple

from .class_registry import ClassRegistry
from .initialise_classes import identify_definition_type
from .utils import split_props_by_required, pascal_to_snake


def add_properties_to_classes():
    """
    Adds properties to dynamically generated classes based on their JSON schema definitions.

    This function iterates through all classes registered in the ClassRegistry that are marked as "custom".
    It retrieves their definitions, separates properties into required and non-required categories,
    and adds them to the respective classes using specific type hints. Additionally, it handles the inclusion
    of arbitrary additional properties if specified in the schema.

    The function concludes by adjusting the initialization methods for classes that involve passthrough or
    multi-inheritance to ensure they properly integrate properties from all parent classes.
    """
    for class_name, cls in ClassRegistry._registry.items():
        if ClassRegistry.get_definition_type(class_name) == "custom":
            definition = ClassRegistry.get_definition(class_name)
            required_props, non_required_props = split_props_by_required(definition)
            for prop_name, prop in required_props.items():
                prop_type = identify_definition_type(prop)
                type_hint = create_type_hint(prop_type, class_name, prop_name)
                add_property_to_class(cls, prop_name, type_hint, is_optional=False)
            for prop_name, prop in non_required_props.items():
                prop_type = identify_definition_type(prop)
                type_hint = create_type_hint(prop_type, class_name, prop_name)
                add_property_to_class(cls, prop_name, type_hint, is_optional=True)
            if "additionalProperties" in definition:
                add_additional_properties_to_class(
                    cls, definition.get("additionalProperties")
                )
    replace_init_in_passthrough_classes()
    combine_inits_in_multiinheritance()


def add_property_to_class(
    cls: Type, prop_name: str, type_hint: Type, is_optional: bool
) -> None:
    """
    Add a property to a class based on schema information.

    Args:
        cls (Type): The class to modify.
        prop_name (str): The name of the property to add.
        type_hint (Type): The type hint for the property.
        is_optional (bool): Indicates whether the property is optional.

    """
    snake_case_name = pascal_to_snake(prop_name)
    if is_optional:
        cls.add_property(
            snake_case_name, Optional[type_hint], description=None, default=None
        )  # TODO: Replace with actual description if available
    else:
        cls.add_property(
            snake_case_name, type_hint, description=None
        )  # TODO: Replace with actual description if available


def add_additional_properties_to_class(
    cls: Type, additional_properties_definition: Dict
):
    """
    Adds support for additional, arbitrary properties to a class based on the schema definition provided.

    This function identifies the type of additional properties allowed in the schema and applies a type hint
    to the class for handling these properties.

    Args:
        cls (Type): The class to which additional properties will be added.
        additional_properties_definition (Dict): The schema definition for the additional properties.
    """
    prop_type = identify_definition_type(additional_properties_definition)
    cls.add_additional_properties(create_type_hint(prop_type, None, None))


def replace_init_in_passthrough_classes():
    """
    Updates initialization methods for classes designated as passthrough to directly use their parent's __init__.

    This function ensures that passthrough classes, which are meant to inherit behavior directly from a parent class,
    use the parent's initialization method, maintaining the intended inheritance and initialization logic.
    """
    for class_name, def_type in ClassRegistry._definition_types.items():
        if def_type == "passthrough":
            cls = ClassRegistry.get_class(class_name)
            parent_class = cls.mro()[1]
            cls.__init__ = parent_class.__init__
            cls._type_hints = parent_class._type_hints


def combine_inits_in_multiinheritance():
    """
    Combine initialization methods from multiple parent classes for classes with multi-inheritance.

    This function calls a method to combine the initialization methods from multiple inheritance hierarchies,
    ensuring that all parent initializations are properly executed in classes that inherit from multiple parents.
    """
    for class_name, def_type in ClassRegistry._definition_types.items():
        if def_type == "multi-inheritance":
            cls = ClassRegistry.get_class(class_name)
            cls._combine_multiinheritance_inits()


def create_type_hint(prop_type_tuple: Tuple, class_name: str, prop_name: str) -> Any:
    """
    Creates a type hint based on the property type information provided.

    This function processes property type metadata to generate appropriate Python type hints,
    facilitating the dynamic generation and registration of classes and their properties.

    Args:
        prop_type_tuple (Tuple): A tuple containing the property type information, including the base type, any specific Python type,
                           reference names, and the associated definition.
        class_name (str): The name of the class to which the property belongs.
        prop_name (str): The name of the property for which the type hint is being created.

    Returns:
        Any: A Python type or a composite type constructed based on the provided property type information.
    """
    if not prop_type_tuple:
        return None
    prop_type, python_type, ref_name, _ = prop_type_tuple
    if prop_type == "native":
        return python_type
    elif prop_type == "passthrough":
        return ClassRegistry.get_class(ref_name)
    elif prop_type == "list":
        return List[create_type_hint(python_type, prop_name, ref_name)]
    elif prop_type == "union":
        return Union[
            tuple(create_type_hint(a, prop_name, ref_name) for a in python_type)
        ]
    elif prop_type == "custom":
        return ClassRegistry.get_class(f"{class_name}_{pascal_to_snake(prop_name)}")
    else:
        return None
