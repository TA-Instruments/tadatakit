from .schema_loader import load_schema
from .definition_registry import DefinitionRegistry

schema = load_schema()

definition_registry = DefinitionRegistry(schema)

definition_registry.register_in_globals(globals())
