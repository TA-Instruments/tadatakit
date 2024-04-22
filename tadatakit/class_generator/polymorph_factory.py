from typing import Dict


class PolymorphFactory:
    """
    A factory for creating polymorphic schema objects based on conditional JSON Schema properties.

    This class is designed to manage the instantiation of different schema objects depending on conditions
    specified in the JSON Schema. It evaluates these conditions to dynamically create the correct type
    based on runtime data.

    Attributes:
        definition_registry (DefinitionRegistry): The registry containing all schema definitions, type hints, and casters.
        conditions (List[Dict]): A list of conditions and their corresponding schema references.
    """

    def __init__(self, definition_registry, definition: Dict):
        """
        Initializes the PolymorphFactory with a specific set of JSON Schema conditions.

        Args:
            definition_registry (DefinitionRegistry): The registry that holds type hints and caster functions for all schema definitions.
            definition (Dict): The specific part of the schema that defines conditions for choosing the schema references.

        Raises:
            KeyError: If the required condition fields are not present in the definition.
        """
        self.definition_registry = definition_registry
        self.conditions = definition["allOf"]

    def discriminate(self, data_dict: Dict):
        """
        Determines and instantiates the correct schema object type based on the conditions specified in the JSON Schema.

        This method evaluates each condition in the `allOf` list to find the first match based on the `if` clause
        and then uses the `then` clause to determine which schema reference to use for instantiation.

        Args:
            data_dict (Dict): The data dictionary containing the necessary data to evaluate conditions and instantiate the object.

        Returns:
            SchemaObject: An instance of the correct subclass as determined by the evaluated conditions.

        Raises:
            ValueError: If no conditions match or if the data does not contain necessary fields to evaluate a condition.
        """
        for condition in self.conditions:
            if_clause = condition["if"]["properties"]
            then_clause = condition["then"]["$ref"]
            # Evaluate if all conditions in the if_clause are met
            if all(
                data_dict.get(prop) == value["const"]
                for prop, value in if_clause.items()
            ):
                ref_name = then_clause.split("/")[-1]
                return self.definition_registry._casters[ref_name](data_dict)
        raise ValueError("Data does not match any conditions")
