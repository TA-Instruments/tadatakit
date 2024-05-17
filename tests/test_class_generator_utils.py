import pytest
from datetime import datetime
from uuid import UUID
from typing import Union, List

from tadatakit.class_generator.utils import (
    type_hint_to_str,
    is_instance,
    pascal_to_snake,
    snake_to_pascal,
    json_serializer,
    split_props_by_required,
    copy_function,
)


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (str, "str"),
        (int, "int"),
        (datetime, "datetime"),
        (Union[str, int], "Union[str, int]"),
    ],
)
def test__type_hint_to_str__convert_type_hint_to_string(type_hint, expected):
    assert type_hint_to_str(type_hint) == expected


@pytest.mark.parametrize(
    "obj, type_hint, expected",
    [
        (123, int, True),
        ("abc", str, True),
        ([1, 2, 3], list, True),
        ([1, 2, 3], List[int], True),
        (123, Union[int, str], True),
        ("abc", Union[int, str], True),
        (123, str, False),
    ],
)
def test__is_instance__validate_object_against_type_hint(obj, type_hint, expected):
    assert is_instance(obj, type_hint) == expected


def test__is_instance__raise_type_error__when_type_hint_is_invalid():
    with pytest.raises(TypeError):
        is_instance(123, "not_a_type")


@pytest.mark.parametrize(
    "pascal, snake", [("PascalCase", "pascal_case"), ("TestCase", "test_case")]
)
def test__pascal_to_snake__convert_pascal_case_to_snake_case(pascal, snake):
    assert pascal_to_snake(pascal, set()) == snake


@pytest.mark.parametrize(
    "snake, pascal", [("snake_case", "SnakeCase"), ("test_case", "TestCase")]
)
def test__snake_to_pascal__convert_snake_case_to_pascal_case(snake, pascal):
    assert snake_to_pascal(snake, set()) == pascal


def test__json_serializer__serialize_datetime():
    dt = datetime(2020, 1, 1, 12, 0)
    assert json_serializer(dt) == "2020-01-01T12:00:00.000000Z"


def test__json_serializer__serialize_uuid():
    uid = UUID("12345678123456781234567812345678")
    assert json_serializer(uid) == "12345678-1234-5678-1234-567812345678"


def test__json_serializer__raise_error__when_unsupported_type():
    with pytest.raises(TypeError):
        json_serializer(1.23)


def test__split_props_by_required__separate_required_and_non_required_properties():
    definition = {
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"],
    }
    required_props, non_required_props = split_props_by_required(definition)
    assert "name" in required_props
    assert "age" in non_required_props
    assert "name" not in non_required_props


def create_complex_function():
    x = 10

    def complex_function(a, b: int = 5, *args, **kwargs) -> str:
        """
        A complex function to test copying capabilities.
        """
        return f"Result: {a + b + x}"

    return complex_function


def test__copy_function__copy_complex_function():
    original_function = create_complex_function()
    copied_function = copy_function(original_function)
    assert copied_function is not original_function
    assert copied_function(5) == original_function(5)
    assert copied_function.__code__ is original_function.__code__
    assert copied_function.__globals__ is original_function.__globals__
    assert copied_function.__name__ == original_function.__name__
    assert copied_function.__defaults__ == original_function.__defaults__
    assert copied_function.__annotations__ == original_function.__annotations__
    assert copied_function.__dict__ == original_function.__dict__
    if original_function.__closure__ and copied_function.__closure__:
        original_closure_values = [
            cell.cell_contents for cell in original_function.__closure__
        ]
        copied_closure_values = [
            cell.cell_contents for cell in copied_function.__closure__
        ]
        assert original_closure_values == copied_closure_values
    else:
        assert (
            original_function.__closure__ is None
            and copied_function.__closure__ is None
        )
