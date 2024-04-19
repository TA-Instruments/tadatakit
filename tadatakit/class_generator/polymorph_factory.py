from typing import Dict


class PolymorphFactory:
    """
    A factory for creating polymorphic schema objects based on a discriminator property.

    This class is designed to manage the instantiation of different schema objects depending on a discriminator field
    defined in the schema. It maps discriminator values to corresponding object types, enabling the dynamic creation
    of the correct type based on runtime data.

    Attributes:
        definition_registry (DefinitionRegistry): The registry containing all schema definitions, type hints, and casters.
        discriminator_property (str): The property name used to determine the object type.
        discriminator_mapping (Dict[str, Callable]): A mapping from discriminator values to factory functions
                                                     that instantiate the appropriate schema object.
    """

    def __init__(self, definition_registry, definition: Dict):
        """
        Initializes the PolymorphFactory with a specific discriminator setup.

        Args:
            definition_registry (DefinitionRegistry): The registry that holds type hints and caster functions for all schema definitions.
            definition (Dict): The specific part of the schema that defines the discriminator and its mappings.

        Raises:
            KeyError: If the required discriminator fields are not present in the definition.
        """
        self.definition_registry = definition_registry
        self.discriminator_property = definition["discriminator"]["propertyName"]
        self.discriminator_mapping = {
            mapping_value: self.definition_registry._casters[ref.split("/")[-1]]
            for mapping_value, ref in definition["discriminator"]["mapping"].items()
        }

    def discriminate(self, data_dict: Dict):
        """
        Determines and instantiates the correct schema object type based on the discriminator property in the provided data.

        This method reads the discriminator property from the data dictionary, uses it to look up the appropriate
        factory function, and calls this function to create an instance of the correct schema object.

        Args:
            data_dict (Dict): The data dictionary containing the discriminator property and other necessary data to instantiate the object.

        Returns:
            SchemaObject: An instance of the correct subclass as determined by the discriminator property.

        Raises:
            KeyError: If the discriminator property is missing or if the value does not correspond to any defined mapping.
        """
        return self.discriminator_mapping[data_dict[self.discriminator_property]](
            data_dict
        )
