import json
from typing import Dict
from importlib import resources


def load_schema() -> Dict:
    """
    Load and return the JSON schema from the `tainstruments_triosdataschema` package.

    Returns:
        Dict: The loaded JSON schema as a dictionary.
    """
    with resources.files("tainstruments_triosdataschema").joinpath(
        "TRIOSJSONExportSchema.json"
    ).open("r") as f:
        return json.load(f)
