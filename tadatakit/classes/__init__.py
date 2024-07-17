import pandas as pd
from typing import Dict, Optional, Literal
from uuid import UUID
import warnings

from tadatakit.class_generator import Experiment, DataSetClassificationType


class DataProvenanceWarning(UserWarning):
    pass


warnings.simplefilter("once", DataProvenanceWarning)


def create_dataframe(
    self: Experiment,
    section: Literal["original", "processed"] = "original",
    start_index: Optional[int] = None,
    end_index: Optional[int] = None,
) -> pd.DataFrame:
    """
    Generates a pandas DataFrame from a slice of the results within this Experiment instance.

    This method processes the results of an experiment to create a DataFrame that is useful for
    further analysis or visualization. It optionally slices the results using provided indices.

    Args:
        section (Literal["original", "processed"]): The name of the section to retrieve.
        start_index (Optional[int]): The starting index for slicing the results. Defaults to None, which
                                     starts from the first result.
        end_index (Optional[int]): The ending index for slicing the results. Defaults to None, which
                                   goes up to the last result.

    Returns:
        pd.DataFrame: A DataFrame representation of the Experiment's results, with appropriate
                      data types and units applied to the columns.
    """
    try:
        results = getattr(self.results, section)
    except AttributeError as e:
        raise ValueError(
            f"Section '{section}' does not exist in the Experiment instance."
        ) from e

    column_dtypes: Dict[str, str] = {}
    column_names: Dict[str, str] = {}

    for col, details in results.column_headers.__dict__.items():
        column_dtypes[col] = "float64" if details.value_type == "Number" else "object"
        unit_dict = details.unit
        unit_name = unit_dict.name if unit_dict else None
        column_names[col] = details.display_name
        if unit_name is not None:
            column_names[col] += f" / {unit_name}"

    df = pd.DataFrame([row.__dict__ for row in results.rows[start_index:end_index]])
    df = df.astype({c: column_dtypes[c] for c in df.columns})

    def uuid_converter(x):
        if isinstance(x, str):
            return UUID(x)
        else:
            return None

    for uuid_column in [
        k
        for k, v in results.column_headers.to_dict().items()
        if v["ValueType"] == "Uuid"
    ]:
        df[uuid_column] = df[uuid_column].apply(uuid_converter)

    if (
        section == "original"
        and results.classification is not DataSetClassificationType.UNMODIFIED
    ):
        warnings.warn(
            f'The {section} data for this experiment is classified as "{results.classification.description}"',
            DataProvenanceWarning,
            stacklevel=2,
        )
    return df.rename(columns=column_names)


def get_dataframe(
    self: Experiment,
    section: Literal["original", "processed"] = "original",
) -> pd.DataFrame:
    """
    Retrieves a DataFrame containing all results from the Experiment.

    Args:
        section (Literal["original", "processed"]): The name of the section to retrieve.

    Returns:
        pd.DataFrame: A DataFrame containing all results of the Experiment.
    """
    return create_dataframe(self, section, None, None)


def get_dataframes_by_step(
    self: Experiment,
    section: Literal["original", "processed"] = "original",
) -> Dict[str, pd.DataFrame]:
    """
    Generates a dictionary of pandas DataFrames, each representing the results of a
    specific step in the Experiment.

    This method organizes the experiment results into separate DataFrames for each step
    based on the "Procedure Step Id".

    Args:
        section (Literal["original", "processed"]): The name of the section to retrieve.

    Returns:
        Dict[str, pd.DataFrame]: A dictionary where the keys are step names and the values are DataFrames
                                 containing the results for each respective step.
    """
    df = self.get_dataframe(section)
    df_dict = {k: v for k, v in df.groupby("Procedure Step Id")}
    steps = [step.name for step in self.procedure.steps]
    return steps, [
        df_dict.get(step.id, pd.DataFrame()) for step in self.procedure.steps
    ]


setattr(Experiment, "get_dataframe", get_dataframe)
setattr(Experiment, "get_dataframes_by_step", get_dataframes_by_step)
