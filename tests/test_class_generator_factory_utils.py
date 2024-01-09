import pytest
from pathlib import Path
from tadatakit.class_generator.factory_utils import (
    load_schema,
    register_classes_in_globals,
    get_ref,
    get_ref_path,
    find_refs,
    split_props_by_required,
    type_hint_generator,
    identify_class_of_ref,
)
from tadatakit.class_generator.base_class import SchemaObject

TEST_SCHEMA_FILE = Path(__file__).parent / "test_schema.json"


def test_load_schema():
    schema = load_schema(TEST_SCHEMA_FILE)
    assert isinstance(schema, dict)
    assert "components" in schema
    assert "schemas" in schema["components"]


def test_register_classes_in_globals():
    class_registry = {"ExampleObject": {"class": SchemaObject}}
    globals_dict = {}
    register_classes_in_globals(globals_dict, class_registry)
    assert "ExampleObject" in globals_dict
    assert globals_dict["ExampleObject"] == SchemaObject


def test_get_ref():
    schema = load_schema(TEST_SCHEMA_FILE)
    ref_str = "#/components/schemas/Number"
    ref = get_ref(schema, ref_str)
    assert isinstance(ref, dict)
    assert ref.get("type") == "number"


def test_get_ref_path():
    schema = load_schema(TEST_SCHEMA_FILE)
    ref_path = "components/schemas/Number"
    ref = get_ref_path(schema, ref_path)
    assert isinstance(ref, dict)
    assert ref.get("type") == "number"


def test_find_refs():
    schema = load_schema(TEST_SCHEMA_FILE)
    refs = find_refs(schema)
    assert isinstance(refs, list)
    assert "#/components/schemas/Number" in refs


def test_split_props_by_required():
    schema = load_schema(TEST_SCHEMA_FILE)
    details_schema = get_ref(schema, "#/components/schemas/Experiment")
    required_props, non_required_props = split_props_by_required(details_schema)
    assert "Sample" in required_props
    assert "FinishTime" in non_required_props


def test_type_hint_generator():
    class_registry = {"ExampleObject": {"class": SchemaObject}}
    property_definition = {"type": "string"}
    type_hint = type_hint_generator(property_definition, False, class_registry)
    assert type_hint == str


def test_identify_class_of_ref():
    schema = load_schema(TEST_SCHEMA_FILE)
    example_object_schema = get_ref(schema, "#/components/schemas/Experiment")
    subclass_it, class_type = identify_class_of_ref(example_object_schema)
    assert subclass_it
    assert class_type == SchemaObject


if __name__ == "__main__":
    pytest.main()
