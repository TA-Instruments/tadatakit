import pytest
import pathlib
import os
import json
import pandas
from uuid import UUID

from tadatakit.classes import Experiment


def test__get_dataframe__must_return_expected_data__when_column_names_are_varying_formats():
    directory_path = os.path.dirname(os.path.abspath(__file__))
    input_file_path = os.path.join(directory_path, "test_classes_data/dataset.json")
    experiment = Experiment.from_json(input_file_path)

    actual_data_frame = experiment.get_dataframe("processed")

    expected_file_path = os.path.join(directory_path, "test_classes_data/expected.json")

    expected_file = open(expected_file_path, "r")
    try:
        expected_data = json.load(expected_file)
    finally:
        expected_file.close()

    expected_data_frame = pandas.DataFrame(expected_data["rows"])

    def uuid_converter(x):
        if isinstance(x, str):
            return UUID(x)
        else:
            return None

    for col, data in expected_data["non_float64_type_conversion_columns"].items():
        column_header_data_type = data["ValueType"]
        if column_header_data_type == "Uuid":
            expected_data_frame[col] = expected_data_frame[col].apply(uuid_converter)
        elif column_header_data_type == "Number":
            expected_data_frame = expected_data_frame.astype({col: "float64"})
        else:
            expected_data_frame = expected_data_frame.astype({col: "object"})

    comparison_result = expected_data_frame.compare(actual_data_frame)

    # we expect no values to be returned since this indicates the two data frames have the same contents
    assert comparison_result.size == 0
