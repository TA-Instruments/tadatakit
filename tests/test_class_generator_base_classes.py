import pytest
import json
from datetime import datetime
from uuid import UUID
from io import StringIO

from tadatakit.class_generator.base_classes import SchemaObject


@pytest.fixture
def schema_data():
    return {
        "string_property": "test",
        "integer_property": 42,
        "float_property": 3.14,
        "boolean_property": True,
        "datetime_property": "2020-01-01T00:00:00Z",
        "uuid_property": "123e4567-e89b-12d3-a456-426614174000",
    }


@pytest.fixture
def dynamic_schema_class():
    class TestSchema(SchemaObject):
        pass

    TestSchema._add_property("string_property", str, str)
    TestSchema._add_property("integer_property", int, int)
    TestSchema._add_property("float_property", float, float)
    TestSchema._add_property("boolean_property", bool, bool)
    TestSchema._add_property("uuid_property", UUID, UUID)
    TestSchema._add_property(
        "datetime_property",
        datetime,
        datetime,
        default=datetime.now(),
    )
    return TestSchema


def test__dynamic_property_addition__add_properties_correctly(dynamic_schema_class):
    instance = dynamic_schema_class(
        string_property="value",
        integer_property=100,
        float_property=10.5,
        boolean_property=False,
        datetime_property=datetime.now(),
        uuid_property=UUID("123e4567-e89b-12d3-a456-426614174000"),
    )
    assert instance.string_property == "value"
    assert instance.integer_property == 100
    assert isinstance(instance.datetime_property, datetime)
    assert isinstance(instance.uuid_property, UUID)


def test__SchemaObject_init__raise_error__when_missing_required_properties(
    dynamic_schema_class,
):
    with pytest.raises(TypeError):
        # Missing mandatory uuid_property
        dynamic_schema_class(string_property="value", integer_property=100)


def test__to_dict__convert_instance_to_dict(dynamic_schema_class, schema_data):
    instance = dynamic_schema_class(**schema_data)
    result = instance.to_dict()
    assert result["StringProperty"] == "test"
    assert result["IntegerProperty"] == 42
    assert result["BooleanProperty"] is True
    assert "DatetimeProperty" in result
    assert "UuidProperty" in result


def test__to_json__convert_instance_to_json(dynamic_schema_class, schema_data):
    instance = dynamic_schema_class(**schema_data)
    buffer = StringIO()
    instance.to_json(buffer)
    buffer.seek(0)
    data = json.load(buffer)
    assert data["StringProperty"] == "test"
    assert data["IntegerProperty"] == 42
    assert data["BooleanProperty"] is True


def test__from_dict__create_instance_from_dict(dynamic_schema_class, schema_data):
    instance = dynamic_schema_class.from_dict(schema_data)
    assert instance.string_property == "test"
    assert instance.integer_property == 42


def test__from_json__create_instance_from_json(dynamic_schema_class, schema_data):
    json_data = json.dumps(schema_data)
    buffer = StringIO(json_data)
    instance = dynamic_schema_class.from_json(buffer)
    assert instance.string_property == "test"
    assert instance.integer_property == 42
