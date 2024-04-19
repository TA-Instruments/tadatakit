import pandas as pd
from typing import Dict, Optional
from uuid import UUID

from tadatakit.class_generator import Experiment


def create_dataframe(
    self: Experiment, start_index: Optional[int] = None, end_index: Optional[int] = None
) -> pd.DataFrame:
    """
    Generates a pandas DataFrame from a slice of the results within this Experiment instance.

    This method processes the results of an experiment to create a DataFrame that is useful for
    further analysis or visualization. It optionally slices the results using provided indices.

    Args:
        start_index (Optional[int]): The starting index for slicing the results. Defaults to None, which
                                     starts from the first result.
        end_index (Optional[int]): The ending index for slicing the results. Defaults to None, which
                                   goes up to the last result.

    Returns:
        pd.DataFrame: A DataFrame representation of the Experiment's results, with appropriate
                      data types and units applied to the columns.
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
    df["Procedure Step Id"] = df["Procedure Step Id"].apply(UUID)
    return df.rename(columns=column_names)


def get_dataframe(self: Experiment) -> pd.DataFrame:
    """
    Retrieves a DataFrame containing all results from the Experiment.

    Returns:
        pd.DataFrame: A DataFrame containing all results of the Experiment.
    """
    return create_dataframe(self, None, None)


def get_dataframes_by_step(self: Experiment) -> Dict[str, pd.DataFrame]:
    """
    Generates a dictionary of pandas DataFrames, each representing the results of a
    specific step in the Experiment.

    This method organizes the experiment results into separate DataFrames for each step
    based on the "Procedure Step Id".

    Returns:
        Dict[str, pd.DataFrame]: A dictionary where the keys are step names and the values are DataFrames
                                 containing the results for each respective step.
    """
    df = self.get_dataframe()
    df_dict = {k: v for k, v in df.groupby("Procedure Step Id")}
    steps = [step.name for step in self.procedure.steps]
    return steps, [
        df_dict.get(step.id, pd.DataFrame()) for step in self.procedure.steps
    ]


setattr(Experiment, "get_dataframe", get_dataframe)
setattr(Experiment, "get_dataframes_by_step", get_dataframes_by_step)
