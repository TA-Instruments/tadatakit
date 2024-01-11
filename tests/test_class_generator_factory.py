import pytest
from pathlib import Path
from tadatakit.class_generator.factory_utils import load_schema
from tadatakit.class_generator.factory import (
    initialize_class_registry,
    add_type_hints_to_all_classes,
    populate_classes_with_properties,
)

TEST_SCHEMA_FILE = Path(__file__).parent / "test_schema.json"
SAMPLE_SCHEMA = load_schema(TEST_SCHEMA_FILE)


def test_initialize_class_registry():
    """
    Test if the class registry is initialized correctly.
    """
    class_registry = initialize_class_registry(SAMPLE_SCHEMA)
    assert isinstance(class_registry, dict)
    assert "Experiment" in class_registry


def test_add_type_hints():
    """
    Test if type hints are added correctly to the classes in the class registry.
    """
    class_registry = initialize_class_registry(SAMPLE_SCHEMA)
    class_registry_with_hints = add_type_hints_to_all_classes(class_registry)
    assert "type_hint" in class_registry_with_hints.get("Experiment")
    assert class_registry_with_hints.get("Number").get("type_hint") is float


def test_populate_classes():
    """
    Test if the classes are populated correctly with properties.
    """
    class_registry = initialize_class_registry(SAMPLE_SCHEMA)
    class_registry_with_hints = add_type_hints_to_all_classes(class_registry)
    populated_class_registry = populate_classes_with_properties(
        class_registry_with_hints
    )
    assert len(populated_class_registry["Experiment"]["class"]._added_properties) > 0


# Additional tests can be written for the helper functions if necessary
