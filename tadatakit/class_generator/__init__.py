from pathlib import Path

from .factory import generate_complete_class_registry
from .factory_utils import load_schema, register_classes_in_globals


schema_file_path = Path(__file__).parent.parent.parent / "schema" / "TADataSchema.json"
schema = load_schema(schema_file_path)

class_registry = generate_complete_class_registry(schema)

register_classes_in_globals(globals(), class_registry)
