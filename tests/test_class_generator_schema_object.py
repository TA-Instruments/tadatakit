import pytest
import inspect
from tadatakit.class_generator.schema_object import (
    SchemaObject,
    is_instance,
    is_optional_list_of_schema_objects,
    is_optional_type,
    get_class_from_type_hint,
)
from typing import List, Optional, Union


class MockSchemaObject(SchemaObject):
    pass


def test_schema_object_init_subclass():
    """
    Test the __init_subclass__ method of SchemaObject.
    """
    assert hasattr(MockSchemaObject, "_added_properties")
    assert hasattr(MockSchemaObject, "_type_hints")


def test_schema_object_add_property():
    """
    Test the add_property method of SchemaObject.
    """
    MockSchemaObject.add_property("test_property", int, default=0)
    assert "test_property" in MockSchemaObject._added_properties


def test_schema_object_update_init():
    """
    Test the _update_init method of SchemaObject.
    """
    MockSchemaObject.add_property("test_property", int, default=0)
    assert "test_property" in inspect.signature(MockSchemaObject.__init__).parameters


def test_is_instance():
    """
    Test the is_instance function.
    """
    assert is_instance(5, int)
    assert is_instance([1], List[int])


def test_is_optional_list_of_schema_objects():
    """
    Test the is_optional_list_of_schema_objects function.
    """
    assert is_optional_list_of_schema_objects(Optional[List[SchemaObject]])
    assert is_optional_list_of_schema_objects(Optional[List[MockSchemaObject]])
    assert not is_optional_list_of_schema_objects(List[SchemaObject])


def test_is_optional_type():
    """
    Test the is_optional_type function.
    """
    assert is_optional_type(Optional[int])
    assert is_optional_type(Union[int, None])
    assert not is_optional_type(int)


def test_get_class_from_type_hint():
    """
    Test the get_class_from_type_hint function.
    """
    assert get_class_from_type_hint(Optional[int]) == int
