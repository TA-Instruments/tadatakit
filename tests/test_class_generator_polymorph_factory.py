import pytest
from tadatakit.class_generator.polymorph_factory import PolymorphFactory
from tadatakit.class_generator.definition_registry import DefinitionRegistry


@pytest.fixture
def mock_registry(mocker):
    mock = mocker.MagicMock(spec=DefinitionRegistry)
    mock._casters = {
        "Employee": mocker.MagicMock(return_value="Employee instance created"),
        "Manager": mocker.MagicMock(return_value="Manager instance created"),
    }
    return mock


@pytest.fixture
def conditions_schema():
    return {
        "allOf": [
            {
                "if": {"properties": {"role": {"const": "employee"}}},
                "then": {"$ref": "#/definitions/Employee"},
            },
            {
                "if": {"properties": {"role": {"const": "manager"}}},
                "then": {"$ref": "#/definitions/Manager"},
            },
        ]
    }


def test__PolymorphFactory_init__must_create_conditions__when_provided_with_valid_conditions(
    mock_registry, conditions_schema
):
    factory = PolymorphFactory(mock_registry, conditions_schema)
    assert len(factory.conditions) == 2


def test__PolymorphFactory_init__must_raise_error__when_conditions_are_missing(
    mock_registry,
):
    with pytest.raises(KeyError):
        PolymorphFactory(mock_registry, {})


def test__discriminate__must_return_correct_instance__when_first_condition(
    mock_registry, conditions_schema
):
    factory = PolymorphFactory(mock_registry, conditions_schema)
    result = factory.discriminate({"role": "employee"})
    assert result == "Employee instance created"


def test__discriminate__must_return_correct_instance__when_second_condition(
    mock_registry, conditions_schema
):
    factory = PolymorphFactory(mock_registry, conditions_schema)
    result = factory.discriminate({"role": "manager"})
    assert result == "Manager instance created"


def test__discriminate__must_raise_error__when_no_condition_matches(
    mock_registry, conditions_schema
):
    factory = PolymorphFactory(mock_registry, conditions_schema)
    with pytest.raises(ValueError) as exc_info:
        factory.discriminate({"role": "intern"})
    assert "Data does not match any conditions" in str(exc_info.value)
