import pandas as pd
from typing import Dict
from tadatakit.class_generator import Experiment


def create_dataframe(self: Experiment) -> pd.DataFrame:
    """
    Create a pandas DataFrame from the results in an Experiment object.

    The DataFrame is created using the results in the Experiment object,
    with appropriate data types and column names based on the Experiment's
    result column headers.

    Returns:
        pd.DataFrame: A DataFrame representation of the Experiment's results.
    """
    column_dtypes: Dict[str, str] = {}
    column_names: Dict[str, str] = {}

    for col, details in self.results.column_headers.items():
        column_dtypes[col] = "float64" if details["ValueType"] == "Number" else "object"
        unit_name = details.get("Unit", {"Name": None})["Name"]
        column_names[col] = f"{details['DisplayName']}"
        if unit_name is not None:
            column_names[col] += f" / {unit_name}"

    return (
        pd.DataFrame(self.results.rows)
        .astype(column_dtypes)
        .rename(columns=column_names)
    )


setattr(Experiment, "dataframe", property(create_dataframe))
