from typing import Dict, List, Union, Any, Optional, Tuple, Type, DefaultDict
from datetime import datetime
import uuid
from collections import defaultdict

from .class_registry import ClassRegistry
from .schema_object import SchemaObject
from .utils import pascal_to_snake

# Basic mapping of JSON Schema types to Python types
type_mapping = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}

# Special format handling
format_mapping = {
    "date-time": datetime,
    "uuid": uuid.UUID,
    "byte": bytes,  # For base64 encoded data
}


def get_definitions_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract definitions from a schema's components.

    Args:
        schema (Dict[str, Any]): The schema to parse.

    Returns:
        Dict[str, Any]: A dictionary of schema definitions.
    """
    return schema.get("components", {}).get("schemas", {})


class DefinitionUnidentifiedError(Exception):
    """Custom exception for when schema definition cannot be identified."""


def identify_definition_type(
    definition: Dict[str, Any]
) -> Tuple[str, Optional[Union[List[Tuple], Type]], Optional[str], Dict[str, Any]]:
    """
    Identifies the type of a JSON schema definition and categorizes it for further processing.

    This function analyzes a JSON schema definition and determines its type, such as 'passthrough',
    'multi-inheritance', 'polymorph', 'union', 'custom', 'list', or 'native'. It returns a tuple
    describing the category, relevant types or classifications, a reference name if applicable,
    and the original definition.

    Args:
        definition (Dict[str, Any]): The JSON schema definition to analyze.

    Returns:
        Tuple[str, Optional[Union[List[Tuple], Type]], Optional[str], Dict[str, Any]]:
            A tuple containing:
            - A string indicating the type category.
            - A list of tuples, a type, or None, providing additional detail about the category.
            - A string representing a referenced schema name or None.
            - The original JSON schema definition.

    Raises:
        DefinitionUnidentifiedError: If the definition type cannot be identified or is not supported.
    """
    if not definition:
        return None
    elif "$ref" in definition:
        ref_name = definition["$ref"].split("/")[-1]
        return "passthrough", None, ref_name, definition
    elif "allOf" in definition:
        return (
            "multi-inheritance",
            [
                identify_definition_type(sub_definition)
                for sub_definition in definition["allOf"]
            ],
            None,
            definition,
        )
    elif "oneOf" in definition:
        if "discriminator" in definition:
            return (
                "polymorph",
                [
                    identify_definition_type(sub_definition)
                    for sub_definition in definition["oneOf"]
                ],
                None,
                definition,
            )
        else:
            return (
                "union",
                [
                    identify_definition_type(sub_definition)
                    for sub_definition in definition["oneOf"]
                ],
                None,
                definition,
            )
    elif (def_type := definition.get("type")) in type_mapping:
        python_type = type_mapping[def_type]
        format = format_mapping.get(definition.get("format"))
        python_type = format if format is not None else python_type
        if def_type == "object":
            return "custom", None, None, definition
        elif def_type == "array":
            (
                classification,
                python_type,
                ref_name,
                sub_definition,
            ) = identify_definition_type(definition["items"])
            return (
                "list",
                (classification, python_type, ref_name, sub_definition),
                None,
                definition,
            )
        else:
            return "native", python_type, None, definition
    else:
        raise DefinitionUnidentifiedError(f"{definition}")


def groupby_definition_type(
    schema: Dict[str, Any]
) -> DefaultDict[str, Dict[str, Tuple]]:
    """
    Groups schema definitions by their identified type categories.

    This function retrieves definitions from a given schema and uses `identify_definition_type`
    to categorize each definition. It then groups these definitions by their type categories
    into a dictionary, organizing them for easier access and processing based on their types.

    Args:
        schema (Dict[str, Any]): The JSON schema to analyze and group.

    Returns:
        DefaultDict[str, Dict[str, Tuple]]: A dictionary where each key is a definition type
            category (e.g., 'passthrough', 'multi-inheritance'), and the value is another
            dictionary mapping the definition names to their identified type tuples.
    """
    definitions = get_definitions_from_schema(schema)
    definition_identities = {
        k: identify_definition_type(v) for k, v in definitions.items()
    }
    definition_groups = defaultdict(dict)
    for key, value in definition_identities.items():
        group_key = value[0]
        definition_groups[group_key][key] = value
    return definition_groups


def add_native_types_to_class_registry(native_definitions: Dict):
    """
    Registers native type definitions in the class registry.

    This function iterates over a dictionary of native type definitions and registers each
    as a class using the ClassRegistry. Native types directly map to Python built-in types.

    Args:
        native_definitions (Dict): A dictionary of native definitions.
    """
    for class_name, (
        definition_type,
        native_type,
        _,
        definition,
    ) in native_definitions.items():
        ClassRegistry.register_class(
            class_name, native_type, definition, definition_type
        )


def add_custom_types_to_class_registry(custom_definitions: Dict):
    """
    Registers custom type definitions in the class registry.

    This function iterates over a dictionary of custom type definitions and registers each
    by creating a new class that inherits from SchemaObject, then registering it in the ClassRegistry.

    Args:
        custom_definitions (Dict): A dictionary of custom definitions.
    """
    for class_name, (definition_type, _, _, definition) in custom_definitions.items():
        stub_class = type(class_name, (SchemaObject,), {})
        ClassRegistry.register_class(
            class_name, stub_class, definition, definition_type
        )


def add_passthrough_types_to_class_registry(passthrough_definitions: Dict):
    """
    Registers passthrough type definitions in the class registry.

    Passthrough types are those which are defined to directly extend another class, often from external references.
    This function registers each passthrough type by inheriting from the parent class and then registering the new class.

    Args:
        passthrough_definitions (Dict): A dictionary of passthrough definitions.
    """
    for class_name, (
        definition_type,
        _,
        parent_class_name,
        definition,
    ) in passthrough_definitions.items():
        parent_class = ClassRegistry.get_class(parent_class_name)
        stub_class = type(class_name, (parent_class,), {})
        ClassRegistry.register_class(
            class_name, stub_class, definition, definition_type
        )


def add_multiinheritance_types_to_class_registry(multiinheritance_definitions: Dict):
    """
    Registers multiple inheritance type definitions in the class registry.

    Multiple inheritance types combine features from several parent classes. This function dynamically
    creates and registers a class that inherits from multiple parent classes based on the definition details provided.

    Args:
        multiinheritance_definitions (Dict): A dictionary of multi-inheritance definitions.
    """
    for class_name, (
        definition_type,
        parent_class_details,
        _,
        definition,
    ) in multiinheritance_definitions.items():
        parent_classes = []
        undefined_class_count = 0
        for (
            parent_class_classification,
            python_type,
            parent_class_name,
            parent_class_definition,
        ) in parent_class_details:
            if parent_class_classification == "passthrough":
                parent_classes.append(ClassRegistry.get_class(parent_class_name))
            elif parent_class_classification == "custom":
                new_parent_class_name = f"{class_name}_Parent{undefined_class_count}"
                stub_class = type(new_parent_class_name, (SchemaObject,), {})
                ClassRegistry.register_class(
                    new_parent_class_name,
                    stub_class,
                    parent_class_definition,
                    parent_class_classification,
                )
                parent_classes.append(ClassRegistry.get_class(new_parent_class_name))
                undefined_class_count += 1
            else:
                raise DefinitionUnidentifiedError(
                    f"`{parent_class_classification}` not supported for a parent ",
                    "class in a multi-inheritance-type definition",
                )
        stub_class = type(class_name, tuple(parent_classes), {})
        ClassRegistry.register_class(
            class_name, stub_class, definition, definition_type
        )


def add_list_types_to_class_registry(list_definitions: Dict):
    """
    Registers list type definitions in the class registry.

    This function iterates over a dictionary of list type definitions, each describing how to handle a list of items
    based on a schema. It registers each class to handle lists of specific item types, which could be passthrough
    or custom defined types.

    Args:
        list_definitions (Dict): A dictionary of list definitions.
    """
    for class_name, (
        definition_type,
        (item_class_classification, _, item_class_name, item_definition),
        _,
        definition,
    ) in list_definitions.items():
        if item_class_classification == "passthrough":
            item_class = ClassRegistry.get_class(item_class_name)
        elif item_class_classification == "custom":
            item_class_name = f"{class_name}_Item"
            stub_class = type(item_class_name, (SchemaObject,), {})
            ClassRegistry.register_class(
                item_class_name, stub_class, item_definition, item_class_classification
            )
            item_class = ClassRegistry.get_class(item_class_name)
        ClassRegistry.register_class(
            class_name, List[item_class], definition, definition_type
        )


def add_union_types_to_class_registry(union_definitions: Dict):
    """
    Registers union type definitions in the class registry.

    This function processes union types, which are schemas specifying that an object could be one of several types.
    It dynamically creates and registers a new class for each union type, allowing objects to validate against any
    of the included types.

    Args:
        union_definitions (Dict): A dictionary of union definitions.
    """
    for class_name, (
        definition_type,
        definition_types,
        _,
        definition,
    ) in union_definitions.items():
        classes = [ClassRegistry.get_class(a[2]) for a in definition_types]
        ClassRegistry.register_class(
            class_name, Union[tuple(classes)], definition, definition_type
        )


def add_polymorph_types_to_class_registry(polymorph_definitions: Dict):
    """
    Registers polymorphic type definitions in the class registry.

    Polymorphic types use union definitions to handle cases where an object can conform to one of many defined types,
    often differentiated by a discriminator field. This function delegates to `add_union_types_to_class_registry`
    to handle the registration of these polymorphic types for now.

    Args:
        polymorph_definitions (Dict): A dictionary of polymorphic definitions.
    """
    add_union_types_to_class_registry(polymorph_definitions)


def add_classes_from_props():
    """
    Dynamically generates and registers new classes for properties that have custom types.

    This function scans through all registered classes marked as "custom" in the Class Registry,
    inspects their properties, and for each property that itself needs a custom class,
    dynamically creates and registers that class. This supports nested custom objects within the schema.
    """
    classes_to_add_from_props = []
    for class_name, cls in ClassRegistry._registry.items():
        if ClassRegistry.get_definition_type(class_name) == "custom":
            definition = ClassRegistry.get_definition(class_name)
            for prop_name, prop_def in definition.get("properties", {}).items():
                prop_type, _, _, definition = identify_definition_type(prop_def)
                if prop_type == "custom":
                    classes_to_add_from_props.append(
                        (
                            f"{class_name}_{pascal_to_snake(prop_name)}",
                            type(
                                f"{class_name}_{pascal_to_snake(prop_name)}",
                                (SchemaObject,),
                                {},
                            ),
                            definition,
                            prop_type,
                        )
                    )
    for class_name, cls, definition, prop_type in classes_to_add_from_props:
        ClassRegistry.register_class(class_name, cls, definition, prop_type)


def initialise_class_registry(schema: Dict):
    """
    Initializes the class registry based on a given schema.

    This function categorizes the schema definitions by type and then initializes the class
    registry by dynamically creating classes for each category of schema definition (native, custom,
    passthrough, multi-inheritance, list, union, and polymorph). It also dynamically generates
    classes for properties that are determined to require custom handling.

    Args:
        schema (Dict): The JSON schema to initialize the class registry from.
    """
    definition_groups = groupby_definition_type(schema)
    add_native_types_to_class_registry(definition_groups.get("native", {}))
    add_custom_types_to_class_registry(definition_groups.get("custom", {}))
    add_passthrough_types_to_class_registry(definition_groups.get("passthrough", {}))
    add_multiinheritance_types_to_class_registry(
        definition_groups.get("multi-inheritance", {})
    )
    add_list_types_to_class_registry(definition_groups.get("list", {}))
    add_union_types_to_class_registry(definition_groups.get("union", {}))
    add_polymorph_types_to_class_registry(definition_groups.get("polymorph", {}))
    add_classes_from_props()
