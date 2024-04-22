import json
from typing import Dict


def load_schema() -> Dict:
    """
    Load and return the JSON schema from the `tainstrumentstriosdataschema` package.

    Returns:
        Dict: The loaded JSON schema as a dictionary.
    """
    # with resources.files("tainstrumentstriosdataschema").joinpath(
    #     "TriosDataSchema.json"
    # ).open("r") as f:
    #     return json.load(f)

    with open("/home/stuartncook/code/tadatakit/examples/json_schema.json") as f:
        schema = json.load(f)
    return schema
