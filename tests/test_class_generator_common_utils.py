import pytest
from tadatakit.class_generator.common_utils import (
    pascal_to_snake,
    snake_to_pascal,
    json_serializer,
)
import datetime


def test_pascal_to_snake():
    assert pascal_to_snake("PascalCase") == "pascal_case"
    assert pascal_to_snake("Pascal") == "pascal"
    assert pascal_to_snake("PascalCaseExample") == "pascal_case_example"
    assert pascal_to_snake("") == ""
    assert pascal_to_snake("Already_snake_case") == "already_snake_case"
    assert pascal_to_snake("JSONData") == "json_data"


def test_snake_to_pascal():
    assert snake_to_pascal("snake_case") == "SnakeCase"
    assert snake_to_pascal("snake") == "Snake"
    assert snake_to_pascal("snake_case_example") == "SnakeCaseExample"
    assert snake_to_pascal("") == ""


def test_json_serializer_datetime():
    dt = datetime.datetime(2021, 1, 1, 12, 0)
    expected = "2021-01-01T12:00:00.000000Z"
    assert json_serializer(dt) == expected


def test_json_serializer_unsupported_type():
    with pytest.raises(TypeError):
        json_serializer({"unsupported": "object"})


if __name__ == "__main__":
    pytest.main()
