from .schema_loader import load_schema
from .initialise_classes import initialise_class_registry
from .populate_classes import add_properties_to_classes
from .class_registry import ClassRegistry

schema = load_schema()

initialise_class_registry(schema)

add_properties_to_classes()

ClassRegistry.register_in_globals(globals())
