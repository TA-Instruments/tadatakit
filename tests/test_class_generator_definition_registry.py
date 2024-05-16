import pytest
from tadatakit.class_generator.definition_registry import (
    DefinitionRegistry,
    DefinitionUnidentifiedError,
)


@pytest.fixture
def simple_schema():
    return {
        "title": "SimpleSchema",
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"],
    }


@pytest.fixture
def complex_schema():
    return {
        "title": "ComplexSchema",
        "type": "object",
        "$defs": {
            "Person": {
                "type": "object",
                "properties": {"Name": {"type": "string"}, "Age": {"type": "integer"}},
                "required": ["Name"],
            },
            "Employee": {
                "allOf": [
                    {"$ref": "#/$defs/Person"},
                    {
                        "type": "object",
                        "properties": {"EmployeeId": {"type": "string"}},
                    },
                ]
            },
        },
        "properties": {"Employee": {"$ref": "#/$defs/Employee"}},
    }


@pytest.fixture
def invalid_schema():
    return {
        "title": "InvalidSchema",
        "type": "object",
        "properties": {
            "name": {"type": "undefinedType"}  # Intentionally incorrect type
        },
    }


def test_initialization_with_simple_schema(simple_schema):
    registry = DefinitionRegistry(simple_schema)
    assert "SimpleSchema" in registry._type_hints


def test_initialization_from_json_file(mocker, simple_schema):
    mocker.patch("json.load", return_value=simple_schema)
    mocker.patch("builtins.open", mocker.mock_open())

    registry = DefinitionRegistry.from_json("path/to/schema.json")
    assert "SimpleSchema" in registry._type_hints


def test_error_handling_for_invalid_file(mocker):
    mocker.patch("builtins.open", side_effect=IOError)

    with pytest.raises(IOError):
        DefinitionRegistry.from_json("path/to/nonexistent/file.json")


def test_error_in_schema_parsing(invalid_schema):
    with pytest.raises(DefinitionUnidentifiedError):
        DefinitionRegistry(invalid_schema)


def test_identify_definition_type_with_ref(complex_schema):
    registry = DefinitionRegistry(complex_schema)
    employee_type = registry._identify_definition_type(
        complex_schema["$defs"]["Employee"]
    )
    assert employee_type == "multi-inheritance"


def test_add_types_by_group(complex_schema):
    registry = DefinitionRegistry(complex_schema)
    registry._add_types_by_group("multi-inheritance")
    assert "Employee" in registry._type_hints
    assert callable(registry._casters["Employee"])


def test_property_addition_to_custom_types(complex_schema):
    registry = DefinitionRegistry(complex_schema)
    registry._add_custom_types_from_props()
    registry._add_properties_to_custom_types()
    employee_class = registry._type_hints["Employee"]
    assert "employee_id" in employee_class.__init__.__signature__.parameters


def test_handling_of_additional_properties(simple_schema):
    # Modifying schema to add additionalProperties
    simple_schema["additionalProperties"] = {"type": "string"}
    registry = DefinitionRegistry(simple_schema)
    registry._add_properties_to_custom_types()
    assert registry._type_hints["SimpleSchema"]._kwargs_property is not None


def test_multiinheritance_class_initialization(complex_schema):
    registry = DefinitionRegistry(complex_schema)
    Employee = registry._type_hints["Employee"]
    employee_instance = Employee(name="John Doe", age=30, employee_id="E12345")
    assert employee_instance.name == "John Doe"
    assert employee_instance.age == 30
    assert employee_instance.employee_id == "E12345"


def test_parsing_nested_structures(complex_schema):
    registry = DefinitionRegistry(complex_schema)
    assert registry._type_hints["Person"]
    assert registry._type_hints["Employee"]
