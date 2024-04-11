from typing import Any, Type, Union, get_origin, get_args, Optional, List, Dict, TextIO
import inspect
from functools import wraps
import datetime
import dateutil
import json
import os

from .utils import json_serializer, snake_to_pascal, pascal_to_snake, copy_function


class SchemaObject:
    """
    A base class for dynamically generated schema objects.

    This class allows adding properties dynamically based on a JSON schema. It handles
    the dynamic creation of an __init__ method with the correct signature and type checks.
    """

    _added_properties = None
    _type_hints = None
    _doc_string_base: str
    _kwargs_type_hint = None

    def __init_subclass__(cls, **kwargs: Any):
        """
        Initialize a subclass.

        This method is automatically called during the creation of subclasses of SchemaObject.
        It initializes dictionaries for added properties and type hints, and modifies the
        from_dict and from_json methods' docstrings and return annotations to match the subclass.

        Args:
            **kwargs (Any): Arbitrary keyword arguments that are passed to the parent class.
        """
        super().__init_subclass__(**kwargs)
        cls._added_properties = {}
        cls._type_hints = {}
        cls._doc_string_base = f"A TA Instruments `{cls.__name__}` object.\n\nArgs:"
        cls._kwargs_type_hint = None
        cls._update_init()

        # clean up docstrings
        from_dict_copy = copy_function(cls.from_dict)
        from_dict_copy.__annotations__["return"] = cls.__name__
        from_dict_copy.__doc__ = from_dict_copy.__doc__.replace(
            "SchemaObject", cls.__name__
        )
        cls.from_dict = classmethod(from_dict_copy)
        from_json_copy = copy_function(cls.from_json)
        from_json_copy.__annotations__["return"] = cls.__name__
        from_json_copy.__doc__ = from_json_copy.__doc__.replace(
            "SchemaObject", cls.__name__
        )
        cls.from_json = classmethod(from_json_copy)

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

        This method adds a property to the class with an associated type hint, default value, and description.
        It updates the __init__ method of the class to include this property.

        Args:
            name (str): The name of the property to add.
            type_hint (Type): The type hint for the property, indicating the expected data type.
            default (Any, optional): The default value for the property, if any. Defaults to inspect.Parameter.empty.
            description (str, optional): A brief description of the property. Defaults to an empty string.
        """
        cls._added_properties[name] = (default, description)
        cls._type_hints[name] = type_hint
        cls._update_init()

    @classmethod
    def add_additional_properties(cls, type_hint: Type = Any):
        """
        Enable the schema object class to accept arbitrary keyword arguments (kwargs) with a specified type hint.

        This method allows the class to accept additional properties not explicitly defined in the schema,
        which are captured as kwargs in the __init__ method.

        Args:
            type_hint (Type, optional): The type hint for the additional properties. Defaults to Any.
        """
        if type_hint is None:
            type_hint = Any
        cls._kwargs_type_hint = type_hint
        cls._update_init()

    @classmethod
    def _combine_multiinheritance_inits(cls):
        """
        Combine __init__ methods from multiple inheritance dynamically.

        This method constructs a new __init__ method that integrates __init__ methods from all parent classes,
        handling properties and kwargs appropriately. It ensures that all parent initializations are respected.
        """
        parameters = [
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        doc_string = cls._doc_string_base

        kwargs_type_hint = None

        for supercls in cls.__mro__[1:-2]:
            for name, (default, description) in supercls._added_properties.items():
                param_kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
                parameters.append(inspect.Parameter(name, param_kind, default=default))
                type_hint_str = supercls._get_type_hint_string(
                    supercls._type_hints[name]
                )
                doc_string += f"\n    {name} ({type_hint_str})"
                if description:
                    doc_string += ": {description}"

            if supercls._kwargs_type_hint is not None:
                kwargs_type_hint = supercls._kwargs_type_hint

        if kwargs_type_hint is not None:
            type_hint_str = cls._get_type_hint_string(kwargs_type_hint)
            doc_string += f"\n    **kwargs: Dict[str, {type_hint_str}] (optional)"
            parameters.append(
                inspect.Parameter("kwargs", inspect.Parameter.VAR_KEYWORD)
            )

        new_sig = inspect.Signature(parameters)

        @wraps(cls.__init__)
        def replacement_init_function(self, *args, **kwargs):
            bound_args = new_sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            super_kwargs = {}
            for supercls in cls.__mro__[1:-2]:
                super_params = inspect.signature(supercls.__init__).parameters
                for name, value in bound_args.arguments.items():
                    if name != "self" and name != "kwargs" and name in super_params:
                        super_kwargs[name] = value
                if "kwargs" in super_params:
                    for name, value in bound_args.arguments.get("kwargs", {}).items():
                        super_kwargs[name] = value
                supercls.__init__(self, **super_kwargs)

        cls.__init__ = replacement_init_function
        cls.__init__.__signature__ = new_sig
        cls.__init__.__doc__ = doc_string

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

        if cls._kwargs_type_hint is not None:
            type_hint_str = cls._get_type_hint_string(cls._kwargs_type_hint)
            doc_string += f"\n    **kwargs: Dict[str, {type_hint_str}] (optional)"
            parameters.append(
                inspect.Parameter("kwargs", inspect.Parameter.VAR_KEYWORD)
            )

        new_sig = inspect.Signature(parameters)

        @wraps(cls.__init__)
        def replacement_init_function(self, *args, **kwargs):
            bound_args = new_sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            for name, value in bound_args.arguments.items():
                if name != "self" and name != "kwargs":
                    expected_type = cls._type_hints[name]
                    if value is not None and not is_instance(value, expected_type):
                        try:
                            class_for_casting = get_class_from_type_hint(expected_type)
                            if class_for_casting is datetime.datetime:
                                value = dateutil.parser.parse(value)
                            else:
                                value = class_for_casting(value)
                        except (ValueError, TypeError) as e:
                            raise TypeError(
                                f"Argument '{name}' must be of type {expected_type} (value:{value}, type:{type(value)})"
                            ) from e
                    setattr(self, name, value)

            if "kwargs" in bound_args.arguments and cls._kwargs_type_hint is not None:
                for key, value in bound_args.arguments["kwargs"].items():
                    expected_type = cls._kwargs_type_hint
                    if value is not None and not is_instance(value, expected_type):
                        try:
                            class_for_casting = get_class_from_type_hint(expected_type)
                            if class_for_casting is datetime.datetime:
                                value = dateutil.parser.parse(value)
                            else:
                                value = class_for_casting(value)
                        except (ValueError, TypeError) as e:
                            raise TypeError(
                                f"Argument '{name}' must be of type {expected_type} (value:{value}, type:{type(value)})"
                            ) from e
                    self.__dict__[key] = value

        cls.__init__ = replacement_init_function
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
    def from_json(cls, path_to_json: str) -> "SchemaObject":
        """
        Initialize an instance of the class from a JSON file.

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
        Recursive method to instantiate objects from a dictionary.

        Args:
            data_dict (dict): The dictionary containing data to instantiate the object.
            path (str): A string representing the current path in the object hierarchy.

        Returns:
            SchemaObject: An instance of the class initialized with data from the dictionary.

        Raises:
            TypeError: If a required argument is missing or if there is a type mismatch.
        """
        kwargs = {}
        for kw, value in data_dict.items():
            snake_case_name = pascal_to_snake(kw)
            current_path = f"{path}.{kw}" if path else kw
            if snake_case_name in cls._type_hints:
                type_hint = cls._type_hints.get(snake_case_name)
            else:
                type_hint = cls._kwargs_type_hint
            kwargs[snake_case_name] = cls.process_value(value, type_hint, current_path)

        try:
            return cls(**kwargs)
        except TypeError as e:
            raise TypeError(
                f"Error at {path} (while constructing {cls.__name__}): {str(e)}"
            ) from e

    @staticmethod
    def process_value(value: Any, type_hint: Type, current_path: str) -> Any:
        """
        Processes a value according to its type hint and the current path within the object hierarchy.

        This method processes the given value based on the provided type hint. It handles complex types, such as lists of
        SchemaObject instances or optional types. The processing ensures that the value conforms to the expected type,
        performing necessary conversions or validations.

        Args:
            value (Any): The value to be processed.
            type_hint (Type): The type hint for the value, which may indicate a simple type, a SchemaObject subclass,
                            or a complex structure like lists or unions.
            current_path (str): The current path within the object hierarchy, used for error reporting and tracking during recursion.

        Returns:
            Any: The processed value, potentially converted or validated against the type hint.

        Raises:
            TypeError: If the value cannot be converted to the required type or if any type constraint is violated.
        """
        try:
            if type_hint is None or type_hint == Any:
                processed_value = value
            elif is_optional_list_of_schema_objects(type_hint):
                list_type = get_args(get_args(type_hint)[0])[0]
                if value is not None:
                    processed_value = [
                        list_type.from_dict(item, f"{current_path}[{index}]")
                        for index, item in enumerate(value)
                    ]
            elif inspect.isclass(type_hint) and issubclass(type_hint, SchemaObject):
                processed_value = type_hint.from_dict(value, current_path)
            elif is_optional_type(type_hint) and issubclass(
                get_args(type_hint)[0], SchemaObject
            ):
                if value is not None:
                    processed_value = get_args(type_hint)[0].from_dict(
                        value, current_path
                    )
            elif get_origin(type_hint) is list and issubclass(
                get_args(type_hint)[0], SchemaObject
            ):
                processed_value = [
                    get_args(type_hint)[0].from_dict(item, f"{current_path}[{index}]")
                    for index, item in enumerate(value)
                ]
            else:
                processed_value = value
        except (TypeError, AttributeError) as e:
            raise TypeError(f"Error at {current_path}: {str(e)}") from e

        return processed_value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the instance to a dictionary representation compatible with the schema.

        This method recursively converts all properties of the SchemaObject, including nested SchemaObject instances,
        into a dictionary format.

        Returns:
            Dict[str, Any]: A dictionary representation of the SchemaObject instance.
        """
        result = {}
        for prop_name, value in self.__dict__.items():
            if isinstance(value, SchemaObject):
                result[snake_to_pascal(prop_name)] = value.to_dict()
            elif (
                isinstance(value, list) and value and isinstance(value[0], SchemaObject)
            ):
                result[snake_to_pascal(prop_name)] = [item.to_dict() for item in value]
            else:
                result[snake_to_pascal(prop_name)] = value
        return result

    def to_json(self, path_or_file: Union[str, os.PathLike, TextIO]) -> None:
        """
        Write the instance to a JSON file.

        This method saves the dictionary representation of the SchemaObject instance
        to a specified JSON file, file object, pathlib Path, or any object implementing os.PathLike.

        Args:
            path_or_file (Union[str, os.PathLike, TextIO]): The file path where the JSON should be saved,
                                                                   a file object to write to, or an object representing
                                                                   a file system path
        """
        if isinstance(path_or_file, (str, os.PathLike)):
            with open(path_or_file, "w") as file:
                json.dump(self.to_dict(), file, indent=4, default=json_serializer)
        else:
            json.dump(self.to_dict(), path_or_file, indent=4, default=json_serializer)


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
        if type_hint is Any:
            return True
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
