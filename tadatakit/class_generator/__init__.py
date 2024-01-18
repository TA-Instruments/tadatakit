from .factory import generate_complete_class_registry
from .factory_utils import load_schema, register_classes_in_globals

schema = load_schema()

class_registry = generate_complete_class_registry(schema)

register_classes_in_globals(globals(), class_registry)
