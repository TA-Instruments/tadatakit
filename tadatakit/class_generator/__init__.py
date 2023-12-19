from pathlib import Path

from .factory import class_registry_factory
from .utils import load_schema, register_classes_in_globals


schema_file_path = Path(__file__).parent.parent.parent / "schema" / "TADataSchema.json"
schema = load_schema(schema_file_path)

start_ref = "#/components/schemas/Experiment"
class_registry = class_registry_factory(schema, start_ref)

register_classes_in_globals(globals(), class_registry)
