import pytest
from tadatakit.class_generator.common_utils import pascal_to_snake, snake_to_pascal


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


if __name__ == "__main__":
    pytest.main()
