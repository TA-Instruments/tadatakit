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

    for col, details in self.results.column_headers.to_dict().items():
        column_dtypes[col] = "float64" if details["ValueType"] == "Float" else "object"
        unit_dict = details.get("Unit")
        unit_name = unit_dict["Name"] if unit_dict else None
        column_names[col] = details["DisplayName"]
        if unit_name is not None:
            column_names[col] += f" / {unit_name}"

    df = pd.DataFrame(
        [row.__dict__ for row in self.results.rows[start_index:end_index]]
    )
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


def get_dataframes_by_step(self: Experiment) -> List[Optional[pd.DataFrame]]:
    """
    Create a list of pandas DataFrames, each representing the results of a step in the Experiment.

    Args:
        self (Experiment): The Experiment instance.

    Returns:
        List[Optional[pd.DataFrame]]: A list of DataFrames, one for each step in the Experiment's procedure.
    """
    df = self.get_dataframe()
    df_dict = {k: v for k, v in df.groupby("Procedure Step Id")}
    steps = [step.name for step in self.procedure.steps]
    return steps, [
        df_dict.get(step_id, pd.DataFrame()) for step_id in self.procedure.steps
    ]


setattr(Experiment, "get_dataframe", get_dataframe)
setattr(Experiment, "get_dataframes_by_step", get_dataframes_by_step)
