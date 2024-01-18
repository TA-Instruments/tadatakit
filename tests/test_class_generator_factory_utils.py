import pytest
from pathlib import Path
from tadatakit.class_generator.factory_utils import (
    load_schema,
    register_classes_in_globals,
    get_schema_object_by_ref,
    recursively_find_refs,
    split_props_by_required,
    generate_type_hint,
    lookup_class_of_ref,
)
from tadatakit.class_generator.schema_object import SchemaObject


def test_load_schema():
    schema = load_schema()
    assert isinstance(schema, dict)
    assert "components" in schema
    assert "schemas" in schema["components"]


def test_register_classes_in_globals():
    class_registry = {"ExampleObject": {"class": SchemaObject}}
    globals_dict = {}
    register_classes_in_globals(globals_dict, class_registry)
    assert "ExampleObject" in globals_dict
    assert globals_dict["ExampleObject"] == SchemaObject


def test_get_schema_object_by_ref():
    schema = load_schema()
    ref_str = "#/components/schemas/Number"
    ref = get_schema_object_by_ref(schema, ref_str)
    assert isinstance(ref, dict)
    assert ref.get("type") == "number"


def test_find_refs():
    schema = load_schema()
    refs = recursively_find_refs(schema)
    assert isinstance(refs, list)
    assert "#/components/schemas/Number" in refs


def test_split_props_by_required():
    schema = load_schema()
    details_schema = get_schema_object_by_ref(schema, "#/components/schemas/Experiment")
    required_props, non_required_props = split_props_by_required(details_schema)
    assert "Sample" in required_props
    assert "FinishTime" in non_required_props


def test_type_hint_generator():
    class_registry = {"ExampleObject": {"class": SchemaObject}}
    property_definition = {"type": "string"}
    type_hint = generate_type_hint(property_definition, False, class_registry)
    assert type_hint == str


def test_identify_class_of_ref():
    schema = load_schema()
    example_object_schema = get_schema_object_by_ref(
        schema, "#/components/schemas/Experiment"
    )
    subclass_it, class_type = lookup_class_of_ref(example_object_schema)
    assert subclass_it
    assert class_type == SchemaObject


if __name__ == "__main__":
    pytest.main()
