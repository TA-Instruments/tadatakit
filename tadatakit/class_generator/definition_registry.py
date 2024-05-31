from typing import Dict, Union, TextIO, Any, List, Tuple, Type, Optional
import os
import json
from collections import defaultdict
from datetime import datetime
from dateutil import parser as dateutil_parser
from uuid import UUID
from enum import Enum

from .base_classes import native_type_mapping, SchemaObject, IdDescriptionEnum
from .polymorph_factory import PolymorphFactory
from .utils import pascal_to_snake, split_props_by_required, pascal_to_screaming_snake

# named constants for definition types
NATIVE = "native"
CUSTOM = "custom"
PASSTHROUGH = "passthrough"
MULTIINHERITANCE = "multi-inheritance"
LIST = "list"
UNION = "union"
POLYMORPH = "polymorph"
ENUM = "enum"


class DefinitionUnidentifiedError(Exception):
    """Custom exception for when schema definition cannot be identified."""


class DefinitionRegistry:
    """
    Manages and provides access to schema definitions, type hints, and casting functions based on a given schema.

    This class acts as a registry for all schema definitions extracted from a JSON schema, categorizing and organizing
    them into different types for ease of use in the system. It supports the initialization of objects from these
    definitions, the registration of new type hints, and manages multi-inheritance and polymorphism within the schema
    definitions. This class is central to the dynamic creation and management of data models based on the schema
    provided.

    Attributes:
        _schema (Dict): The complete JSON schema dictionary.
        _type_hints (Dict[str, Type]): A mapping from definition names to their resolved Python type hints.
        _casters (Dict[str, Callable]): A mapping from definition names to functions that cast or transform data into
                                       their corresponding Python types.
        _definitions (Dict): A subset of the schema, focusing on the 'components/schemas' section.
        _definition_identities (Dict[str, str]): A dictionary mapping definition names to their identified type category.
        _definition_groups (DefaultDict[str, List[str]]): A dictionary grouping definition names by their type category.
    """

    def __init__(self, schema: Dict) -> None:
        """
        Initializes the DefinitionRegistry with a schema.

        This constructor takes a JSON schema and sets up the initial state of the registry by extracting relevant
        definitions and preparing type hint and caster mappings. It automatically initializes the definitions to ensure
        that the registry is ready for use immediately after creation.

        Args:
            schema (Dict): The JSON schema from which the registry will extract type definitions and other relevant information.
        """
        self._schema = schema
        self._type_hints = {}
        self._casters = {}
        self._definitions = schema.get("$defs", {})
        self._generate_native_pattern_mapping()
        self._definitions.update(
            {
                schema["title"]: {
                    k: v
                    for k, v in schema.items()
                    if not k.startswith("$") and k != "title"
                }
            }
        )
        self._initialize_definitions()

    def _generate_native_pattern_mapping(self):
        self._native_pattern_mapping = dict()
        if "DateTime" in self._definitions:
            self._native_pattern_mapping[
                self._definitions["DateTime"]["pattern"]
            ] = datetime
        if "Uuid" in self._definitions:
            self._native_pattern_mapping[self._definitions["Uuid"]["pattern"]] = UUID

    @classmethod
    def from_json(
        cls, path_or_file: Union[str, os.PathLike, TextIO]
    ) -> "DefinitionRegistry":
        """
        Creates an instance of `DefinitionRegistry` from a schema stored in a file or file-like object.

        This class method facilitates the initialization of the registry directly from a JSON file or
        a file-like object that outputs JSON. It reads the JSON schema, parses it, and uses it to initialize
        and return a new instance of `DefinitionRegistry`.

        Args:
            path_or_file (Union[str, os.PathLike, TextIO]): The path to the JSON schema file or a file-like object
                                                            that can read from a JSON schema.

        Returns:
            DefinitionRegistry: A newly initialized instance of the registry filled with the data from the provided JSON schema.

        Raises:
            IOError: If the file could not be opened or read.
            JSONDecodeError: If the JSON data is not properly formatted.
        """
        if isinstance(path_or_file, (str, os.PathLike)):
            with open(path_or_file, "r") as file:
                schema = json.load(file)
        else:
            schema = json.load(path_or_file)

        return cls(schema)

    def _initialize_definitions(self):
        """
        Initializes and categorises schema definitions from the loaded schema.

        This method organizes the schema definitions by their type and establishes mappings and relationships
        necessary for the registry's functionality. It categorizes definitions into types such as native, custom,
        passthrough, multi-inheritance, list, union, and polymorph. Each type is then processed to set up appropriate
        type hints and casting functions. Finally, it adds custom properties to types and sets up additional properties
        as required.

        The order of operations ensures that dependencies are respected, i.e., base types are defined before they are used
        in complex constructs like multi-inheritance or polymorphic types.

        This method should be called once during the initialization phase of the registry to prepare it for use.

        Returns:
            None
        """
        self._group_schema_by_definition_type()
        # add them in order
        for definition_type in [
            NATIVE,
            ENUM,
            CUSTOM,
            PASSTHROUGH,
            MULTIINHERITANCE,
            LIST,
            UNION,
            POLYMORPH,
        ]:
            self._add_types_by_group(definition_type)
        self._add_custom_types_from_props()
        self._add_properties_to_custom_types()

    def _group_schema_by_definition_type(self):
        """
        Groups schema definitions by their identified type categories.

        This method uses the `identify_definition_type` method to categorize each definition from the internal
        schema dictionary. It then organizes these definitions into groups based on their identified
        types, storing them in a dictionary. This organization facilitates easier access and systematic
        processing of definitions based on their categories such as 'native', 'custom', 'passthrough',
        'multi-inheritance', 'list', 'union', and 'polymorph'.

        The categorized definitions are stored internally and used for initializing the registry and
        processing type-specific logic.

        Returns:
            None
        """
        self._definition_identities = {
            k: self._identify_definition_type(v) for k, v in self._definitions.items()
        }
        self._definition_groups = defaultdict(list)
        for key, value in self._definition_identities.items():
            self._definition_groups[value].append(key)

    def _identify_definition_type(self, definition: Dict[str, Any]):
        """
        Identifies the type category of a given schema definition based on its structure and content.

        This method examines the keys and values in a schema definition to determine its appropriate type
        category. The definitions are categorized as follows:
        - 'passthrough': Definitions that refer directly to another definition using `$ref`.
        - 'multi-inheritance': Definitions that use `allOf` indicating inheritance from multiple types.
        - 'polymorph': Definitions using `allOf` with conditions, typically involving 'if' and 'then' to support polymorphic behavior.
        - 'union': Definitions using `oneOf` or `anyOf` to represent a union of types.
        - 'custom': Definitions representing complex objects.
        - 'list': Definitions representing arrays.
        - 'native': Definitions that map directly to native Python types.

        Args:
            definition (Dict[str, Any]): The schema definition to analyze.

        Returns:
            str: The category type of the definition.

        Raises:
            DefinitionUnidentifiedError: If the definition does not match any known pattern or if it lacks
                                         required elements to determine its type.
        """
        if "$ref" in definition:
            return PASSTHROUGH
        elif "allOf" in definition:
            if all(
                "if" in condition and "then" in condition
                for condition in definition["allOf"]
            ):
                return POLYMORPH
            else:
                return MULTIINHERITANCE
        elif "oneOf" in definition or "anyOf" in definition:
            return UNION
        elif (def_type := definition.get("type")) in native_type_mapping:
            if def_type == "object":
                return CUSTOM
            elif def_type == "array":
                return LIST
            else:
                return NATIVE
        elif "enum" in definition:
            return ENUM
        else:
            raise DefinitionUnidentifiedError(
                f"Unable to identify definition type for: {definition}"
            )

    def _create_type_hint_and_caster(  # noqa: C901
        self, definition: Dict, definition_name: str = None
    ) -> Tuple[Type, Any]:
        """
        Creates a type hint and a corresponding caster function for a given schema definition.

        This method analyzes a schema definition to determine the appropriate Python type and
        the function required to cast or convert JSON data into instances of that type. It handles
        various schema configurations including references to other definitions (`$ref`),
        combinations of definitions (`allOf` for multi-inheritance, `allOf` with conditions for polymorphism,
        `oneOf` or `anyOf` for unions), and direct mappings to native Python types.

        Args:
            definition (Dict): The schema definition to analyze.
            definition_name (str, optional): The name to use for any dynamically created types,
                                             particularly useful in complex schema structures
                                             like multi-inheritance and polymorph cases.

        Returns:
            Tuple[Type, Any]: A tuple where the first element is the Python type that the definition
                              corresponds to, and the second is a function that can cast data to that type.

        Raises:
            DefinitionUnidentifiedError: If the definition type cannot be identified or is not supported,
                                         indicating that the definition is malformed or incomplete.
        """
        if not definition:
            return Any, lambda x: x
        elif "$ref" in definition:
            ref_name = definition["$ref"].split("/")[-1]
            ref_type_hint = self._type_hints[ref_name]
            if not isinstance(ref_type_hint, SchemaObject):
                return ref_type_hint, self._casters[ref_name]
            elif definition_name is not None:
                PassthroughClass = type(
                    definition_name, (self._type_hints[ref_name],), {}
                )
                return PassthroughClass, PassthroughClass.from_dict
            else:
                ref_type_hint = self._type_hints[ref_name]
                ref_caster = self._casters[ref_name]
                return ref_type_hint, ref_caster
        elif "allOf" in definition:
            if any("if" in cond and "then" in cond for cond in definition["allOf"]):
                union_type_hints = []
                for allof_definition in definition["allOf"]:
                    then_definition = allof_definition["then"]
                    then_definition_type = self._identify_definition_type(
                        then_definition
                    )
                    if then_definition_type == PASSTHROUGH:
                        ref_name = then_definition["$ref"].split("/")[-1]
                        union_type_hints.append(self._type_hints[ref_name])
                    else:
                        raise DefinitionUnidentifiedError(
                            f"{then_definition} not supported for polymorph definitions"
                        )
                polymorph_factory = PolymorphFactory(self, definition)
                type_hint = Union[tuple(union_type_hints)]
                return type_hint, polymorph_factory.discriminate
            parent_classes = []
            undefined_class_count = 0
            for parent_definition in definition["allOf"]:
                parent_definition_type = self._identify_definition_type(
                    parent_definition
                )
                if parent_definition_type == PASSTHROUGH:
                    ref_name = parent_definition["$ref"].split("/")[-1]
                    ParentClass = self._type_hints[ref_name]
                    parent_classes.append(ParentClass)
                elif parent_definition_type == CUSTOM:
                    new_parent_class_name = (
                        f"{definition_name}_Parent{undefined_class_count}"
                    )
                    stub_class = type(new_parent_class_name, (SchemaObject,), {})
                    self._definitions[new_parent_class_name] = parent_definition
                    self._type_hints[new_parent_class_name] = stub_class
                    self._casters[new_parent_class_name] = stub_class
                    self._definition_identities[new_parent_class_name] = CUSTOM
                    self._definition_groups[CUSTOM].append(new_parent_class_name)
                    parent_classes.append(stub_class)
                else:
                    raise DefinitionUnidentifiedError(
                        f"`{parent_definition_type}` not supported for a parent ",
                        "class in a multi-inheritance-type definition",
                    )
            MultiinheritanceClass = type(definition_name, tuple(parent_classes), {})
            return MultiinheritanceClass, MultiinheritanceClass.from_dict
        elif "oneOf" in definition or "anyOf" in definition:
            union_type_hints = []
            for oneof_definition in definition.get("oneOf", definition.get("anyOf")):
                oneof_definition_type = self._identify_definition_type(oneof_definition)
                if oneof_definition_type == PASSTHROUGH:
                    ref_name = oneof_definition["$ref"].split("/")[-1]
                    union_type_hints.append(self._type_hints[ref_name])
                else:
                    raise DefinitionUnidentifiedError(
                        f"{oneof_definition} not supported for `oneOf` of `anyOf` definitions"
                    )
            type_hint = Union[tuple(union_type_hints)]
            return type_hint, lambda x: x
        elif (def_type := definition.get("type")) in native_type_mapping:
            if def_type == "object":
                if definition_name in self._type_hints:
                    type_hint = self._type_hints[definition_name]
                    caster = self._casters[definition_name]
                else:
                    type_hint = type(definition_name, (SchemaObject,), {})
                    caster = type_hint.from_dict
                    self._definitions[definition_name] = definition
                    self._type_hints[definition_name] = type_hint
                    self._casters[definition_name] = caster
                    self._definition_identities[definition_name] = CUSTOM
                    self._definition_groups[CUSTOM].append(definition_name)
                return type_hint, caster
            elif def_type == "array":
                item_definition = definition["items"]
                item_definition_type = self._identify_definition_type(item_definition)
                if item_definition_type == PASSTHROUGH:
                    ref_name = item_definition["$ref"].split("/")[-1]
                    item_type_hint = self._type_hints[ref_name]
                    item_caster = self._casters[ref_name]
                elif item_definition_type == CUSTOM:
                    item_class_name = f"{definition_name}_Item"
                    item_type_hint = type(item_class_name, (SchemaObject,), {})
                    item_caster = item_type_hint.from_dict
                    self._definitions[item_class_name] = item_definition
                    self._type_hints[item_class_name] = item_type_hint
                    self._casters[item_class_name] = item_caster
                    self._definition_identities[item_class_name] = CUSTOM
                    self._definition_groups[CUSTOM].append(item_class_name)
                else:
                    raise DefinitionUnidentifiedError(
                        f"Item type: `{item_definition_type}` not supported for an array"
                    )
                return List[item_type_hint], lambda x: [item_caster(a) for a in x]
            python_type = native_type_mapping[def_type]
            pattern = self._native_pattern_mapping.get(definition.get("pattern"))
            if pattern is not None:
                python_type = pattern
            type_hint = python_type
            caster = dateutil_parser.parse if python_type == datetime else python_type
            return type_hint, caster
        elif "enum" in definition:
            enum_class = Enum(
                "Classification",
                {
                    pascal_to_screaming_snake(member["Id"]): (
                        member["Id"],
                        member["Description"],
                    )
                    for member in definition["enum"]
                },
                type=IdDescriptionEnum,
            )
            return enum_class, enum_class.from_dict
        else:
            raise DefinitionUnidentifiedError(f"{definition}")

    def _add_types_by_group(self, definition_type: str):
        """
        Processes and registers type hints and casters for all definitions in a specific category.

        This method iterates through all definitions categorized under a given type (e.g., 'native', 'custom',
        'passthrough', etc.) and creates the appropriate Python type hints and caster functions for each.
        These are then registered in the internal mappings, preparing them for use in instantiating schema objects.

        Args:
            definition_type (str): The category of definitions to process, which should correspond to one of the
                                   keys in the `_definition_groups` dictionary (e.g., 'native', 'custom').

        Returns:
            None
        """
        for definition_name in self._definition_groups.get(definition_type, []):
            definition = self._definitions[definition_name]
            type_hint, caster = self._create_type_hint_and_caster(
                definition, definition_name
            )
            self._type_hints[definition_name] = type_hint
            self._casters[definition_name] = caster

    def _add_custom_types_from_props(self):
        """
        Registers new custom types derived from the properties of existing custom definitions.

        This method iterates over all 'custom' definitions and examines each property within these definitions.
        For properties identified as requiring custom type handling (i.e., those categorized as 'custom'), this
        method dynamically creates new SchemaObject subclasses named after the property. These new types are then
        registered within the definition registry, enabling them to be used like any other schema-defined object.

        This approach allows complex nested structures within custom objects to be fully represented and instantiated
        as standalone types when necessary.

        Returns:
            None
        """
        for definition_name in self._definition_groups[CUSTOM]:
            definition = self._definitions[definition_name]
            for property_name, property_definition in definition.get(
                "properties", {}
            ).items():
                prop_def_type = self._identify_definition_type(property_definition)
                if prop_def_type == CUSTOM:
                    prop_class_name = (
                        f"{definition_name}_{pascal_to_snake(property_name, set())}"
                    )
                    prop_type_hint = type(prop_class_name, (SchemaObject,), {})
                    self._definitions[prop_class_name] = property_definition
                    self._type_hints[prop_class_name] = prop_type_hint
                    self._casters[prop_class_name] = prop_type_hint
                    self._definition_identities[prop_class_name] = CUSTOM
                    self._definition_groups[CUSTOM].append(prop_class_name)

    def _add_properties_to_custom_types(self):
        """
        Adds properties to custom types defined in the schema, distinguishing between required and optional properties.

        This method iterates over all custom type definitions and extracts their properties, which are categorized as
        either required or optional. Each property is then added to the corresponding custom type along with an appropriate
        type hint and caster function. This setup allows the custom types to fully represent the schema definitions
        they are derived from, including handling of additional properties if specified in the schema.

        For properties that are not required, the method assigns a default value of None, effectively making them optional.
        It also handles the initialization of these properties to ensure that the custom types are ready for instantiation
        with data conforming to the schema.

        Lastly, if 'additionalProperties' is defined in the schema, it adds support for dynamically named properties not
        explicitly defined in the schema (i.e. kwargs).

        Returns:
            None
        """
        for definition_name in self._definition_groups[CUSTOM]:
            definition = self._definitions[definition_name]
            cls = self._type_hints[definition_name]
            required_props, non_required_props = split_props_by_required(definition)
            for prop_name, prop_definition in required_props.items():
                type_hint, caster = self._create_type_hint_and_caster(
                    prop_definition, f"{definition_name}_{prop_name}"
                )
                cls._add_property(
                    pascal_to_snake(prop_name, cls._special_names_set),
                    caster,
                    type_hint,
                )
            for prop_name, prop_definition in non_required_props.items():
                type_hint, caster = self._create_type_hint_and_caster(
                    prop_definition, f"{definition_name}_{prop_name}"
                )
                cls._add_property(
                    pascal_to_snake(prop_name, cls._special_names_set),
                    caster,
                    Optional[type_hint],
                    default=None,
                )
            if "additionalProperties" in definition:
                type_hint, caster = self._create_type_hint_and_caster(
                    definition.get("additionalProperties")
                )
                cls._add_additional_properties(caster, type_hint)
        self._combine_inits_in_multiinheritance()

    def _replace_init_in_passthrough_classes(self):
        """
        Updates the initialization methods for classes designated as passthrough to directly use their parent's __init__.

        Passthrough classes are meant to act nearly identically to another class, often with very little to no modification
        to the behavior. This method iterates through all passthrough classes, setting their initialization method to
        that of their parent class. It effectively links the child class directly to the parent, ensuring that instances
        of the passthrough class are initialized in the same way as instances of the parent class.

        This approach helps maintain consistency in behavior and ensures correct inheritance and initialization chains
        are preserved for classes that primarily serve as aliases or direct proxies to other classes, while providing
        the more prescriptive class names from the schema.

        Returns:
            None
        """
        for definition_name in self._definition_groups[PASSTHROUGH]:
            cls = self._type_hints[definition_name]
            parent_class = cls.mro()[1]
            cls.__init__ = parent_class.__init__
            cls._added_properties = parent_class._added_properties
            cls._kwargs_property = parent_class._kwargs_property

    def _combine_inits_in_multiinheritance(self):
        """
        Integrates initialization methods from multiple parent classes for classes defined with multi-inheritance.

        This method ensures that classes which inherit from multiple parent classes correctly integrate the initialization
        processes of all their parents. It addresses the challenge of Python's single inheritance constructor chain by
        manually combining the `__init__` methods from each parent class. This ensures that all parent class constructors
        are called and all necessary initializations from each lineage are performed when an instance of a multi-inherited
        class is created.

        This function iterates over all classes categorized under multi-inheritance, calling a specialized method on
        each to merge their constructors appropriately.

        Returns:
            None
        """
        for definition_name in self._definition_groups[MULTIINHERITANCE]:
            cls = self._type_hints[definition_name]
            cls._combine_multiinheritance_inits()

    def register_in_globals(self, globals_dict: Dict):
        """
        Registers each custom class from the registry into the global namespace.

        This method facilitates easier access to dynamically generated classes by adding them to the global namespace.
        It allows these classes to be accessed directly as if they were regular, statically defined classes within
        the module, enhancing modularity and reusability.

        Args:
            globals_dict (Dict): The global namespace dictionary where class references will be stored, typically
                                 obtained via the `globals()` function in the module where classes need to be accessible.

        Returns:
            None
        """
        for category in [ENUM, CUSTOM, PASSTHROUGH, MULTIINHERITANCE]:
            for definition_name in self._definition_groups[category]:
                globals_dict[definition_name] = self._type_hints[definition_name]
