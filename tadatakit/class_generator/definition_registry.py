from typing import Dict, Union, TextIO, Any, List, Tuple, Type, Optional
import os
import json
from collections import defaultdict
from datetime import datetime
import dateutil

from .base_classes import native_type_mapping, native_format_mapping, SchemaObject
from .polymorph_factory import PolymorphFactory
from .utils import pascal_to_snake, split_props_by_required


class DefinitionUnidentifiedError(Exception):
    """Custom exception for when schema definition cannot be identified."""


class DefinitionRegistry:
    def __init__(self, schema: Dict) -> None:
        self._schema = schema
        self._type_hints = {}
        self._casters = {}
        self._definitions = self._schema.get("components", {}).get("schemas", {})
        self.initialise_definitions()

    @classmethod
    def from_json(
        cls, path_or_file: Union[str, os.PathLike, TextIO]
    ) -> "DefinitionRegistry":
        """
        Initialize a `DefinitionRegistry` from the schema stored in a JSON file.

        Args:
            path_or_file (Union[str, os.PathLike, TextIO]): Path to the JSON input file or a file-like object.

        Returns:
            DefinitionRegistry: An instance of the definition registry.
        """
        if isinstance(path_or_file, (str, os.PathLike)):
            with open(path_or_file, "r") as file:
                schema = json.load(file)
        else:
            schema = json.load(path_or_file)

        return cls(schema)

    def initialise_definitions(self):
        self.group_schema_by_definition_type()
        # add them in order
        for definition_type in [
            "native",
            "custom",
            "passthrough",
            "multi-inheritance",
            "list",
            "union",
            "polymorph",
        ]:
            self.add_types_by_group(definition_type)
        self.add_custom_types_from_props()
        self.add_properties_to_custom_types()

    def group_schema_by_definition_type(self):
        """
        Groups schema definitions by their identified type categories.

        This function retrieves definitions from a given schema and uses `identify_definition_type`
        to categorize each definition. It then groups these definitions by their type categories
        into a dictionary, organizing them for easier access and processing based on their types.

        Args:
            schema (Dict[str, Any]): The JSON schema to analyze and group.

        Returns:
            DefaultDict[str, List[str]]: A dictionary where each key is a definition type
                category (e.g., 'passthrough', 'multi-inheritance'), and the value is a list of
                class names
        """
        self._definition_identities = {
            k: self.identify_definition_type(v) for k, v in self._definitions.items()
        }
        self._definition_groups = defaultdict(list)
        for key, value in self._definition_identities.items():
            self._definition_groups[value].append(key)

    def identify_definition_type(self, definition: Dict[str, Any]):
        if "$ref" in definition:
            return "passthrough"
        elif "allOf" in definition:
            return "multi-inheritance"
        elif "oneOf" in definition:
            if "discriminator" in definition:
                return "polymorph"
            else:
                return "union"
        elif (def_type := definition.get("type")) in native_type_mapping:
            if def_type == "object":
                return "custom"
            elif def_type == "array":
                return "list"
            else:
                return "native"
        else:
            raise DefinitionUnidentifiedError(f"{definition}")

    def _create_type_hint_and_caster(  # noqa: C901
        self, definition: Dict, definition_name: str = None
    ) -> Tuple[Type, Any]:
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
            parent_classes = []
            undefined_class_count = 0
            for parent_definition in definition["allOf"]:
                parent_definition_type = self.identify_definition_type(
                    parent_definition
                )
                if parent_definition_type == "passthrough":
                    ref_name = parent_definition["$ref"].split("/")[-1]
                    ParentClass = self._type_hints[ref_name]
                    parent_classes.append(ParentClass)
                elif parent_definition_type == "custom":
                    new_parent_class_name = (
                        f"{definition_name}_Parent{undefined_class_count}"
                    )
                    stub_class = type(new_parent_class_name, (SchemaObject,), {})
                    self._definitions[new_parent_class_name] = parent_definition
                    self._type_hints[new_parent_class_name] = stub_class
                    self._casters[new_parent_class_name] = stub_class
                    self._definition_identities[new_parent_class_name] = "custom"
                    self._definition_groups["custom"].append(new_parent_class_name)
                    parent_classes.append(stub_class)
                else:
                    raise DefinitionUnidentifiedError(
                        f"`{parent_definition_type}` not supported for a parent ",
                        "class in a multi-inheritance-type definition",
                    )
            MultiinheritanceClass = type(definition_name, tuple(parent_classes), {})
            return MultiinheritanceClass, MultiinheritanceClass.from_dict
        elif "oneOf" in definition:
            union_type_hints = []
            for oneof_definition in definition["oneOf"]:
                oneof_definition_type = self.identify_definition_type(oneof_definition)
                if oneof_definition_type == "passthrough":
                    ref_name = oneof_definition["$ref"].split("/")[-1]
                    union_type_hints.append(self._type_hints[ref_name])
                else:
                    raise DefinitionUnidentifiedError(
                        f"{oneof_definition} not supported for `oneOf` definitions"
                    )
            type_hint = Union[tuple(union_type_hints)]
            if "discriminator" in definition:
                polymorph_factory = PolymorphFactory(self, definition)
                return type_hint, polymorph_factory.discriminate
            else:
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
                    self._definition_identities[definition_name] = "custom"
                    self._definition_groups["custom"].append(definition_name)
                return type_hint, caster
            elif def_type == "array":
                item_definition = definition["items"]
                item_definition_type = self.identify_definition_type(item_definition)
                if item_definition_type == "passthrough":
                    ref_name = item_definition["$ref"].split("/")[-1]
                    item_type_hint = self._type_hints[ref_name]
                    item_caster = self._casters[ref_name]
                elif item_definition_type == "custom":
                    item_class_name = f"{definition_name}_Item"
                    item_type_hint = type(item_class_name, (SchemaObject,), {})
                    item_caster = item_type_hint.from_dict
                    self._definitions[item_class_name] = item_definition
                    self._type_hints[item_class_name] = item_type_hint
                    self._casters[item_class_name] = item_caster
                    self._definition_identities[item_class_name] = "custom"
                    self._definition_groups["custom"].append(item_class_name)
                return List[item_type_hint], lambda x: [item_caster(a) for a in x]
            python_type = native_type_mapping[def_type]
            format = native_format_mapping.get(definition.get("format"))
            python_type = format if format is not None else python_type
            type_hint = python_type
            caster = dateutil.parser.parse if python_type == datetime else python_type
            return type_hint, caster
        else:
            raise DefinitionUnidentifiedError(f"{definition}")

    def add_types_by_group(self, definition_type):
        for definition_name in self._definition_groups.get(definition_type, []):
            definition = self._definitions[definition_name]
            type_hint, caster = self._create_type_hint_and_caster(
                definition, definition_name
            )
            self._type_hints[definition_name] = type_hint
            self._casters[definition_name] = caster

    def add_custom_types_from_props(self):
        for definition_name in self._definition_groups["custom"]:
            definition = self._definitions[definition_name]
            for property_name, property_definition in definition.get(
                "properties", {}
            ).items():
                prop_def_type = self.identify_definition_type(property_definition)
                if prop_def_type == "custom":
                    prop_class_name = (
                        f"{definition_name}_{pascal_to_snake(property_name)}"
                    )
                    prop_type_hint = type(prop_class_name, (SchemaObject,), {})
                    self._definitions[prop_class_name] = property_definition
                    self._type_hints[prop_class_name] = prop_type_hint
                    self._casters[prop_class_name] = prop_type_hint
                    self._definition_identities[prop_class_name] = "custom"
                    self._definition_groups["custom"].append(prop_class_name)

    def add_properties_to_custom_types(self):
        for definition_name in self._definition_groups["custom"]:
            definition = self._definitions[definition_name]
            cls = self._type_hints[definition_name]
            required_props, non_required_props = split_props_by_required(definition)
            for prop_name, prop_definition in required_props.items():
                type_hint, caster = self._create_type_hint_and_caster(
                    prop_definition, f"{definition_name}_{prop_name}"
                )
                cls.add_property(pascal_to_snake(prop_name), caster, type_hint)
            for prop_name, prop_definition in non_required_props.items():
                type_hint, caster = self._create_type_hint_and_caster(
                    prop_definition, f"{definition_name}_{prop_name}"
                )
                cls.add_property(
                    pascal_to_snake(prop_name),
                    caster,
                    Optional[type_hint],
                    default=None,
                )
            if "additionalProperties" in definition:
                type_hint, caster = self._create_type_hint_and_caster(
                    definition.get("additionalProperties")
                )
                cls.add_additional_properties(caster, type_hint)
        self.combine_inits_in_multiinheritance()

    def replace_init_in_passthrough_classes(self):
        """
        Updates initialization methods for classes designated as passthrough to directly use their parent's __init__.

        This function ensures that passthrough classes, which are meant to inherit behavior directly from a parent class,
        use the parent's initialization method, maintaining the intended inheritance and initialization logic.
        """
        for definition_name in self._definition_groups["passthrough"]:
            cls = self._type_hints[definition_name]
            print(cls.__name__)
            parent_class = cls.mro()[1]
            cls.__init__ = parent_class.__init__
            cls._added_properties = parent_class._added_properties
            cls._kwargs_property = parent_class._kwargs_property

    def combine_inits_in_multiinheritance(self):
        """
        Combine initialization methods from multiple parent classes for classes with multi-inheritance.

        This function calls a method to combine the initialization methods from multiple inheritance hierarchies,
        ensuring that all parent initializations are properly executed in classes that inherit from multiple parents.
        """
        for definition_name in self._definition_groups["multi-inheritance"]:
            cls = self._type_hints[definition_name]
            cls._combine_multiinheritance_inits()

    def register_in_globals(self, globals_dict: Dict):
        """
        Register classes in the global namespace.

        This function takes each class from the class registry and adds it
        to the global namespace, allowing these classes to be imported
        from the `class_generator` module.

        Args:
            globals_dict (Dict): The global namespace dictionary.

        Returns:
            None
        """
        for definition_name in self._definition_groups["custom"]:
            globals_dict[definition_name] = self._type_hints[definition_name]
