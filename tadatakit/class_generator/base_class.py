import inspect
from functools import wraps
from typing import Any, Type, Union, get_origin, get_args


class SchemaObject:
    """
    A base class for dynamically generated schema objects.

    This class allows adding properties dynamically based on a JSON schema. It handles
    the dynamic creation of an __init__ method with the correct signature and type checks.
    """

    _added_properties = None
    _type_hints = None
    _doc_string_base: str

    def __init_subclass__(cls, **kwargs):
        """
        Initialize a subclass.

        This method is automatically called when a subclass of SchemaObject is created.
        It initializes class-level dictionaries for added properties and type hints.
        """
        super().__init_subclass__(**kwargs)
        cls._added_properties = {}
        cls._type_hints = {}
        cls._doc_string_base = "A TA Instruments schema object.\n\nArgs:"

    @classmethod
    def add_property(
        cls,
        name: str,
        type_hint: Type,
        default: Any = inspect.Parameter.empty,
        description: str = "",
    ):
        """
        Add a property to the schema object class.

        Args:
            name (str): The name of the property.
            type_hint (Type): The type hint for the property.
            default (Any, optional): The default value for the property. Defaults to inspect.Parameter.empty.
            description (str, optional): A description of the property. Defaults to an empty string.
        """
        cls._added_properties[name] = (default, description)
        cls._type_hints[name] = type_hint
        cls._update_init()

    @classmethod
    def _update_init(cls):
        """
        Update the __init__ method to have the correct signature based on added
        properties.

        This internal method dynamically constructs the __init__ method for the
        class, including proper type checking and documentation.
        """
        parameters = [
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        doc_string = cls._doc_string_base

        for name, (default, description) in cls._added_properties.items():
            param_kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
            parameters.append(inspect.Parameter(name, param_kind, default=default))
            type_hint_str = cls._get_type_hint_string(cls._type_hints[name])
            doc_string += f"\n    {name} ({type_hint_str})"
            if description:
                doc_string += ": {description}"

        new_sig = inspect.Signature(parameters)

        @wraps(cls.__init__)
        def new_init(self, *args, **kwargs):
            bound_args = new_sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            for name, value in bound_args.arguments.items():
                if name != "self":
                    expected_type = cls._type_hints[name]
                    if not is_instance(value, expected_type) and value is not None:
                        raise TypeError(
                            f"Argument '{name}' must be of type {expected_type}"
                        )
                    setattr(self, name, value)

        cls.__init__ = new_init
        cls.__init__.__signature__ = new_sig
        cls.__init__.__doc__ = doc_string

    @staticmethod
    def _get_type_hint_string(type_hint: Type) -> str:
        """
        Get a string representation of a type hint.

        Args:
            type_hint (Type): The type hint to convert to a string.

        Returns:
            str: A string representation of the type hint.
        """
        try:
            return type_hint.__name__
        except AttributeError:
            return (
                type_hint.__str__()
                .replace("typing.", "")
                .replace("tadatakit.class_generator.factory.", "")
            )

    def __init__(self, **kwargs):
        """
        Initialize a SchemaObject instance.

        This method is dynamically replaced to match the signature of the added properties.
        """
        pass


def is_instance(obj: Any, type_hint: Type) -> bool:
    """
    Custom type check that understands typing module constructs.

    Args:
        obj (Any): The object to check.
        type_hint (Type): The type hint against which the object is to be checked.

    Returns:
        bool: True if obj is an instance of type_hint, False otherwise.
    """
    if get_origin(type_hint) is Union:
        return any(is_instance(obj, arg) for arg in get_args(type_hint))
    elif isinstance(obj, type_hint):
        return True
    elif get_origin(type_hint) is list and isinstance(obj, list):
        element_type = get_args(type_hint)[0]
        return all(isinstance(elem, element_type) for elem in obj)
    return False
