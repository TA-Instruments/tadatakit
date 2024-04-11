from typing import Dict, Type


class ClassNotFound(Exception):
    """Custom exception for when a class is not found in the registry."""


class ClassRegistry:
    """
    A registry for dynamically generated classes.

    This class handles the registration and retrieval of dynamically generated classes based on JSON schemas.
    """

    _registry = {}
    _definitions = {}
    _definition_types = {}

    @classmethod
    def register_class(
        cls,
        class_name: str,
        class_reference: Type,
        raw_definition: Dict,
        definition_type: str,
    ):
        """
        Registers a dynamically generated class within the class registry.

        This method adds a new class to the registry along with its associated schema definition
        and classification type. The registry is used to manage and retrieve class instances
        based on schema definitions dynamically.

        Args:
            class_name (str): The name of the class to register, used as a key in the registry.
            class_reference (Type): The class itself, typically a reference to a dynamically
                created class.
            raw_definition (Dict): The raw schema definition associated with the class, providing
                the structural details that define the class properties.
            definition_type (str): The type of definition (e.g., 'custom', 'native', 'passthrough'),
                categorizing the class for appropriate processing and instantiation.
        """
        cls._registry[class_name] = class_reference
        cls._definitions[class_name] = raw_definition
        cls._definition_types[class_name] = definition_type

    @classmethod
    def get_class(cls, class_name: str):
        """
        Retrieve a class by name. Raises ClassNotFound if the class does not exist in the registry.

        Args:
            class_name (str): The name of the class to retrieve.

        Returns:
            The class reference if found in the registry.

        Raises:
            ClassNotFound: If the class is not found in the registry.
        """
        if class_name not in cls._registry:
            raise ClassNotFound(f"Class '{class_name}' not found in registry.")
        return cls._registry[class_name]

    @classmethod
    def get_definition(cls, class_name: str):
        """
        Retrieve a raw definition by name. Raises ClassNotFound if the class does not exist in the registry.

        Args:
            class_name (str): The name of the definition to retrieve.

        Returns:
            The raw definition if found in the registry.

        Raises:
            ClassNotFound: If the class is not found in the registry.
        """
        if class_name not in cls._definitions:
            raise ClassNotFound(f"Class '{class_name}' not found in registry.")
        return cls._definitions[class_name]

    @classmethod
    def get_definition_type(cls, class_name: str):
        """
        Retrieve a definition type by name. Raises ClassNotFound if the class does not exist in the registry.

        Args:
            class_name (str): The name of the definition type to retrieve.

        Returns:
            The definition type if found in the registry.

        Raises:
            ClassNotFound: If the class is not found in the registry.
        """
        if class_name not in cls._definition_types:
            raise ClassNotFound(f"Class '{class_name}' not found in registry.")
        return cls._definition_types[class_name]

    @classmethod
    def register_in_globals(cls, globals_dict: Dict):
        """
        Register classes in the global namespace.

        This function takes each class from the class registry and adds it
        to the global namespace, allowing these classes to be imported
        from the `class_generator` module.

        Args:
            globals_dict (Dict): The global namespace dictionary.

        Returns:
            None
        """
        for class_name, registry_class in cls._registry.items():
            globals_dict[class_name] = registry_class
