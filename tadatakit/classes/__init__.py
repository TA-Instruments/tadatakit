import pandas as pd
from typing import Dict, Optional, List, Tuple
from tadatakit.class_generator import Experiment, Procedure


def create_dataframe(
    self: Experiment, start_index: Optional[int] = None, end_index: Optional[int] = None
) -> pd.DataFrame:
    """
    Create a pandas DataFrame from the results in an Experiment object.

    Args:
        self (Experiment): The Experiment instance.
        start_index (Optional[int]): The starting index for slicing the results. Defaults to None.
        end_index (Optional[int]): The ending index for slicing the results. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame representation of the Experiment's results.
    """
    column_dtypes: Dict[str, str] = {}
    column_names: Dict[str, str] = {}

    for col, details in self.results.column_headers.items():
        column_dtypes[col] = "float64" if details["ValueType"] == "Number" else "object"
        unit_name = details.get("Unit", {"Name": None})["Name"]
        column_names[col] = details["DisplayName"]
        if unit_name is not None:
            column_names[col] += f" / {unit_name}"

    df = pd.DataFrame(self.results.rows[start_index:end_index])
    df = df.astype({c: column_dtypes[c] for c in df.columns})
    return df.rename(columns=column_names)


def get_dataframe(self: Experiment) -> pd.DataFrame:
    """
    Create a pandas DataFrame containing all results from the Experiment object.

    Args:
        self (Experiment): The Experiment instance.

    Returns:
        pd.DataFrame: A DataFrame containing all results of the Experiment.
    """
    return create_dataframe(self, None, None)


def get_step_indices(self: Procedure) -> List[Tuple[int, int]]:
    """
    Get the start and end indices for each step in a Procedure.

    Args:
        self (Procedure): The Procedure instance.

    Returns:
        List[Tuple[int, int]]: A list of tuples containing start and end indices for each step.
    """
    return [
        (
            step.results_mapping["StartIndex"],
            step.results_mapping["StartIndex"] + step.results_mapping["Count"],
        )
        if step.results_mapping is not None
        else None
        for step in self.steps
    ]


def get_dataframes_by_step(self: Experiment) -> List[Optional[pd.DataFrame]]:
    """
    Create a list of pandas DataFrames, each representing the results of a step in the Experiment.

    Args:
        self (Experiment): The Experiment instance.

    Returns:
        List[Optional[pd.DataFrame]]: A list of DataFrames, one for each step in the Experiment's procedure.
    """
    return [
        create_dataframe(self, indices[0], indices[1]) if indices is not None else None
        for indices in self.procedure.get_step_indices()
    ]


setattr(Experiment, "get_dataframe", get_dataframe)
setattr(Procedure, "get_step_indices", get_step_indices)
setattr(Experiment, "get_dataframes_by_step", get_dataframes_by_step)
