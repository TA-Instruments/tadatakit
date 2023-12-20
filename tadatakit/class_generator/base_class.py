import inspect
import json
import datetime
from functools import wraps
from typing import Any, Type, Union, get_origin, get_args, Optional, List, Dict

from .common_utils import json_serializer, snake_to_pascal


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
                    if value is not None and not is_instance(value, expected_type):
                        try:
                            class_for_casting = get_class_from_type_hint(expected_type)
                            if class_for_casting is datetime.datetime:
                                value = datetime.datetime.strptime(
                                    value, "%Y-%m-%dT%H:%M:%S.%fZ"
                                )
                            else:
                                value = class_for_casting(value)
                        except (ValueError, TypeError) as e:
                            print(get_class_from_type_hint(expected_type))
                            raise TypeError(
                                f"Argument '{name}' must be of type {expected_type} (value:{value}, type:{type(value)})"
                            ) from e
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

    @classmethod
    def from_json(cls, path_to_json: str):
        """
        Initialize an instance of the class from a JSON file or string that conforms to the schema.

        Args:
            path_to_json (str): Path to the JSON input file.

        Returns:
            SchemaObject: An instance of the class initialized with data from the JSON input.
        """
        with open(path_to_json, "r") as file:
            data = json.load(file)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data_dict: dict, path: str = "") -> "SchemaObject":
        """
        Recursive helper method to instantiate objects from a dictionary.

        Args:
            data_dict (dict): The dictionary containing data to instantiate the object.
            path (str): A string representing the current path in the object hierarchy.

        Returns:
            SchemaObject: An instance of the class initialized with data from the dictionary.

        Raises:
            TypeError: If a required argument is missing or if there is a type mismatch.
        """
        kwargs = {}
        for prop_name, type_hint in cls._type_hints.items():
            pascal_case_name = snake_to_pascal(prop_name)
            current_path = f"{path}.{pascal_case_name}" if path else pascal_case_name

            if pascal_case_name in data_dict:
                value = data_dict[pascal_case_name]
                try:
                    if is_optional_list_of_schema_objects(type_hint):
                        list_type = get_args(get_args(type_hint)[0])[0]
                        if value is not None:
                            kwargs[prop_name] = [
                                list_type._from_dict(item, f"{current_path}[{index}]")
                                for index, item in enumerate(value)
                            ]
                    elif inspect.isclass(type_hint) and issubclass(
                        type_hint, SchemaObject
                    ):
                        kwargs[prop_name] = type_hint.from_dict(value, current_path)
                    elif is_optional_type(type_hint) and issubclass(
                        get_args(type_hint)[0], SchemaObject
                    ):
                        if value is not None:
                            kwargs[prop_name] = get_args(type_hint)[0]._from_dict(
                                value, current_path
                            )
                    elif get_origin(type_hint) is list and issubclass(
                        get_args(type_hint)[0], SchemaObject
                    ):
                        kwargs[prop_name] = [
                            get_args(type_hint)[0]._from_dict(
                                item, f"{current_path}[{index}]"
                            )
                            for index, item in enumerate(value)
                        ]
                    else:
                        # print(prop_name, type_hint)
                        kwargs[prop_name] = value
                except (TypeError, AttributeError) as e:
                    raise TypeError(f"Error at {current_path}: {str(e)}") from e
            else:
                # Check if the property is optional
                if not is_optional_type(type_hint):
                    raise TypeError(
                        f"Missing required argument at {current_path} (type_hint:{type_hint})"
                    )

        try:
            return cls(**kwargs)
        except TypeError as e:
            raise TypeError(
                f"Error at {path} (while constructing {cls.__name__}): {str(e)}"
            ) from e

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the SchemaObject instance to a dictionary representation compatible with the OpenAPI schema.

        This method recursively converts all properties of the SchemaObject, including nested SchemaObject instances,
        into a dictionary format.

        Returns:
            Dict[str, Any]: A dictionary representation of the SchemaObject instance.
        """
        result = {}
        for prop_name, _ in self._type_hints.items():
            value = getattr(self, prop_name, None)
            if isinstance(value, SchemaObject):
                result[snake_to_pascal(prop_name)] = value.to_dict()
            elif (
                isinstance(value, list) and value and isinstance(value[0], SchemaObject)
            ):
                result[snake_to_pascal(prop_name)] = [item.as_dict() for item in value]
            else:
                result[snake_to_pascal(prop_name)] = value
        return result

    def to_json(self, path_to_json: str) -> None:
        """
        Write the SchemaObject instance to a JSON file.

        This method saves the dictionary representation of the SchemaObject instance
        to a specified JSON file.

        Args:
            path_to_json (str): The file path where the JSON should be saved.
        """
        with open(path_to_json, "w") as file:
            json.dump(self.to_dict(), file, indent=4, default=json_serializer)


def is_instance(obj: Any, type_hint: Type) -> bool:
    """
    Custom type check that understands typing module constructs, such as Union and List.

    Args:
        obj (Any): The object to check.
        type_hint (Type): The type hint against which the object is to be checked.

    Returns:
        bool: True if obj is an instance of type_hint, False otherwise.

    Raises:
        TypeError: If there is an issue with the type hint or the object during type checking.
    """
    try:
        if get_origin(type_hint) is Union:
            return any(is_instance(obj, arg) for arg in get_args(type_hint))
        elif get_origin(type_hint) is list and isinstance(obj, list):
            element_type = get_args(type_hint)[0]
            return all(isinstance(elem, element_type) for elem in obj)
        elif isinstance(obj, type_hint):
            return True
        return False
    except TypeError as e:
        raise TypeError(f"type_hint: {type_hint}, obj: {obj}") from e


def is_optional_list_of_schema_objects(type_hint: Type) -> bool:
    """
    Check if the type hint represents an optional list of SchemaObject subclasses.

    Args:
        type_hint (Type): The type hint to check.

    Returns:
        bool: True if the type hint is an optional list of SchemaObject subclasses, False otherwise.
    """
    if get_origin(type_hint) is Union:
        args = get_args(type_hint)
        return any(arg is type(None) for arg in args) and any(
            get_origin(arg) is list and issubclass(get_args(arg)[0], SchemaObject)
            for arg in args
        )
    return False


def is_optional_type(type_hint: Type) -> bool:
    """
    Check if the type hint is Optional or a Union with None.

    Args:
        type_hint (Type): The type hint to check.

    Returns:
        bool: True if the type hint is Optional or a Union including None, False otherwise.
    """
    if get_origin(type_hint) is Union:
        return any(arg is type(None) for arg in get_args(type_hint))
    return False


def get_class_from_type_hint(type_hint: Type) -> Type:
    """
    Extract the actual class from a type hint, handling Optional and List types.

    Args:
        type_hint (Type): The type hint from which to extract the class.

    Returns:
        Type: The extracted class from the type hint.
    """
    if is_optional_type(type_hint):
        type_hint = get_args(type_hint)[0]
    if get_origin(type_hint) is list:
        type_hint = get_args(type_hint)[0]
    return type_hint
