from abc import ABC
from datetime import datetime
from dateutil import parser as dateutil_parser
from typing import Any, Type, Union, TextIO, Dict
import inspect
from functools import wraps
import json
import os
from enum import Enum

from .utils import (
    type_hint_to_str,
    is_instance,
    snake_to_pascal,
    pascal_to_snake,
    convert_non_json_serializable_types,
    copy_function,
)

native_type_mapping = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


class SchemaObject(ABC):
    """
    Base class for dynamically generated schema objects from schema definitions.

    This class provides a framework for instances that are dynamically created based on JSON schemas,
    supporting automatic property addition, type casting, and initialization based on schema specifications.
    It uses a metaprogramming approach to adapt its structure dynamically to the schema definitions provided.
    This includes handling complex schemas that require custom property management, type coercion, and support
    for additional properties.

    Methods:
        from_json: Class method to create an instance from a JSON file.
        from_dict: Class method to create an instance from a dictionary.
        to_dict: Converts the instance to a dictionary following the schema's structure.
        to_json: Serializes the instance to a JSON file.
    """

    _added_properties = None
    _type_hints = None
    _doc_string_base: str
    _kwargs_property = None

    def __init__(self, **kwargs):
        """
        Initialize a SchemaObject instance.

        This method is dynamically replaced to match the signature of the added properties.
        """
        pass

    def __str__(self):
        """
        Returns a string representation of the SchemaObject instance.

        This method is a simple alias to `__repr__` to ensure the string representation is consistent whether
        `str()` or `repr()` is called on an instance of SchemaObject.

        Returns:
            str: The string representation of the SchemaObject.
        """
        return self.__repr__()

    def __repr__(self):
        """
        Returns a detailed string representation of the SchemaObject instance.

        Constructs a string that includes the class name and a comma-separated list of property-value pairs for
        each property stored in the instance's dictionary. If the resulting string is too long (more than 200 characters),
        it simplifies the output to show only the class name followed by ellipses, indicating a large number of properties
        or extensive data (e.g. `Experiment(...)`).

        Returns:
            str: The detailed string representation of the SchemaObject, possibly abbreviated.
        """
        full_str = f"{self.__class__.__name__}({','.join([f'{k}={v.__repr__()}' for k, v in self.__dict__.items()])})"
        if len(full_str) > 200:
            return f"{self.__class__.__name__}(...)"
        else:
            return full_str

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Customizes subclass initialization to support dynamic property additions and initialization.

        This hook automatically initializes certain class-level attributes that support the dynamic creation and
        management of properties based on schema definitions. It sets up structures to hold added properties,
        constructs a base documentation string, and prepares for additional properties not explicitly defined in
        the schema but allowed by it.

        Args:
            **kwargs (Any): Arbitrary keyword arguments that are passed to the base class's __init_subclass__ method,
                            in case they are needed in the future.

        Returns:
            None
        """
        super().__init_subclass__(**kwargs)
        cls._added_properties = {}
        cls._special_names_set = set()
        cls._doc_string_base = (
            f"Initialize a TA Instruments `{cls.__name__}` object.\n\nArgs:"
        )
        cls._kwargs_property = None
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
    def _add_property(
        cls,
        name: str,
        caster: Any,
        type_hint: Type,
        default: Any = inspect.Parameter.empty,
    ):
        """
        Dynamically adds a property to the class with specified casting and type hinting.

        This method is used internally to add properties to schema objects based on schema definitions.
        Each property can have a type hint and a caster function associated with it, which are used to ensure
        that values assigned to these properties are of the correct type or are coerced into the correct type
        dynamically. A default value can also be specified, which is used if no value is provided when creating
        an instance of the class.

        Args:
            name (str): The name of the property to add.
            caster (Any): A function or type to cast the input value to the correct type. This can be a built-in
                          type like `int` or `str`, or a more complex function that performs validation and conversion.
            type_hint (Type): The type hint for the property, used for documentation and runtime checks in some contexts.
            default (Any, optional): The default value for the property if none is specified. Defaults to `inspect.Parameter.empty`,
                                     which indicates that there is no default value (i.e., the property is required).

        Returns:
            None
        """
        cls._added_properties[name] = {
            "caster": caster,
            "type_hint": type_hint,
            "default": default,
        }
        cls._update_init()

    @classmethod
    def _add_additional_properties(cls, caster: Any = None, type_hint: Type = Any):
        """
        Allows the class to accept additional properties beyond those explicitly defined, with specified type casting.

        This method sets up a mechanism for the class to manage additional properties that are not predefined in the
        schema but are allowed by it. It assigns a caster function and a type hint to these additional properties,
        ensuring they adhere to expected data types or are transformed appropriately upon assignment.

        Args:
            caster (Any, optional): A function to cast values of additional properties to the appropriate type.
                                    If no caster is provided, values will be used as they are given.
            type_hint (Type, optional): A type hint for the additional properties. Defaults to `Any`, which allows
                                        any type of value.

        Returns:
            None
        """
        if type_hint is None:
            type_hint = Any
        cls._kwargs_property = {
            "caster": caster,
            "type_hint": type_hint,
        }
        cls._update_init()

    @classmethod
    def _update_init(cls):
        """
        Dynamically updates the constructor method to incorporate newly added properties and additional keyword arguments.

        This method constructs a new `__init__` method based on dynamically added properties, ensuring that the constructor
        accepts and correctly initializes all properties defined by the schema. It adjusts the constructor's signature to
        include parameters for all registered properties with appropriate type hints and default values. It also handles
        additional properties if they have been enabled for the class.

        The new constructor ensures that each parameter is correctly cast using the provided caster functions and that
        all properties are set on the instance accordingly. If properties are provided via `kwargs` and are not defined
        explicitly in the class, they are also processed and added to the instance.

        Returns:
            None
        """
        parameters = [
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        doc_string = cls._doc_string_base

        for name, property_details in cls._added_properties.items():
            param_kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
            parameters.append(
                inspect.Parameter(
                    name,
                    param_kind,
                    default=property_details["default"],
                    annotation=property_details["type_hint"],
                )
            )
            type_hint_str = type_hint_to_str(property_details["type_hint"])
            doc_string += f"\n    {name} ({type_hint_str})"

        if cls._kwargs_property is not None:
            type_hint_str = type_hint_to_str(cls._kwargs_property["type_hint"])
            doc_string += f"\n    **kwargs: {type_hint_str} (optional)"
            parameters.append(
                inspect.Parameter(
                    "kwargs",
                    inspect.Parameter.VAR_KEYWORD,
                    annotation=cls._kwargs_property["type_hint"],
                )
            )

        new_sig = inspect.Signature(parameters)

        @wraps(cls.__init__)
        def replacement_init_function(self, *args, **kwargs):
            bound_args = new_sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()

            # test and cast types
            for name, value in bound_args.arguments.items():
                if name != "self" and name != "kwargs":
                    expected_type = cls._added_properties[name]["type_hint"]
                    if value is not None and not is_instance(value, expected_type):
                        try:
                            caster = cls._added_properties[name]["caster"]
                            if caster is datetime:
                                value = dateutil_parser.parse(value)
                            else:
                                value = caster(value)
                        except (ValueError, TypeError) as e:
                            raise TypeError(
                                f"Argument '{name}' must be of type {expected_type} (value:{value}, type:{type(value)})"
                            ) from e
                    setattr(self, name, value)

            if "kwargs" in bound_args.arguments and cls._kwargs_property is not None:
                for key, value in bound_args.arguments["kwargs"].items():
                    expected_type = cls._kwargs_property["type_hint"]
                    if value is not None and not is_instance(value, expected_type):
                        try:
                            caster = cls._kwargs_property["caster"]
                            if caster is datetime:
                                value = dateutil_parser.parse(value)
                            else:
                                value = caster(value)
                        except (ValueError, TypeError) as e:
                            raise TypeError(
                                f"Argument '{name}' must be of type {expected_type} (value:{value}, type:{type(value)})"
                            ) from e
                    self.__dict__[key] = value

        cls.__init__ = replacement_init_function
        cls.__init__.__signature__ = new_sig
        cls.__init__.__doc__ = doc_string

    @classmethod
    def _combine_multiinheritance_inits(cls):
        """
        Dynamically creates a unified constructor that merges the initialization processes of multiple inherited classes.

        This method is crucial for classes that inherit from multiple parents with their own custom initialization logic.
        It constructs a new `__init__` method that integrates `__init__` methods from all parent classes, ensuring
        that properties from each parent are initialized appropriately and that all inherited initialization behaviors are
        respected.

        This process involves constructing a new signature that includes all parameters from parent constructors,
        including both explicitly defined properties and `kwargs` if applicable. The resulting `__init__` method
        sets properties on the instance based on these parameters and respects default values and type annotations
        provided by the parent classes.

        Returns:
            None
        """
        parameters = [
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        doc_string = cls._doc_string_base
        added_properties = {}

        for supercls in cls.__mro__[1:-2]:
            if supercls._added_properties is not None:
                for name, property_details in supercls._added_properties.items():
                    param_kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
                    parameters.append(
                        inspect.Parameter(
                            name,
                            param_kind,
                            default=property_details["default"],
                            annotation=property_details["type_hint"],
                        )
                    )
                    type_hint_str = type_hint_to_str(property_details["type_hint"])
                    doc_string += f"\n    {name} ({type_hint_str})"
                added_properties.update(supercls._added_properties)

        for supercls in cls.__mro__[1:-2]:
            if supercls._kwargs_property is not None and "kwargs" not in [
                p.name for p in parameters
            ]:
                type_hint_str = type_hint_to_str(supercls._kwargs_property["type_hint"])
                doc_string += f"\n    **kwargs: Dict[str, {type_hint_str}] (optional)"
                parameters.append(
                    inspect.Parameter(
                        "kwargs",
                        inspect.Parameter.VAR_KEYWORD,
                        annotation=supercls._kwargs_property["type_hint"],
                    ),
                )
                cls._kwargs_property = supercls._kwargs_property

        cls._added_properties = added_properties
        new_sig = inspect.Signature(parameters)

        @wraps(cls.__init__)
        def replacement_init_function(self, *args, **kwargs):
            bound_args = new_sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            for supercls in cls.__mro__[1:-2]:
                super_kwargs = {}
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
    def from_json(cls, path_or_file: Union[str, os.PathLike, TextIO]) -> "SchemaObject":
        """
        Creates an instance of the class by reading from a JSON file or file-like object.

        Note that the file is loaded entirely into memory, and files can be large.

        Args:
            path_or_file (Union[str, os.PathLike, TextIO]): The path to a JSON file or a file-like object
                                                            that can be read from.

        Returns:
            SchemaObject: A new instance of the class, initialized with data extracted from the JSON file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            JSONDecodeError: If the file is not a valid JSON.
            TypeError: If a required property is missing or if there is a type mismatch, indicating that the
                       dictionary does not perfectly align with the class's expected attributes.
        """
        if isinstance(path_or_file, (str, os.PathLike)):
            with open(path_or_file, "r") as file:
                data = json.load(file)
        else:
            data = json.load(path_or_file)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data_dict: Dict) -> "SchemaObject":
        """
        Instantiates an object from a dictionary representation, typically used for deserialization.
        It converts dictionary keys to the appropriate snake_case format expected by the class' attributes,
        if necessary, and then attempts to create an instance by passing the processed dictionary as keyword
        arguments to the class constructor.

        Note that this can take a long time for very large dictionaries.

        Args:
            data_dict (Dict): The dictionary containing data with which to instantiate the object. Keys should
                              correspond to the attribute names of the class and their values to the attribute values.

        Returns:
            SchemaObject: An instance of the class initialized with data from the dictionary.

        Raises:
            TypeError: If a required property is missing or if there is a type mismatch, indicating that the
                       dictionary does not perfectly align with the class's expected attributes.
        """
        data_dict = {
            pascal_to_snake(k, cls._special_names_set): v for k, v in data_dict.items()
        }
        try:
            return cls(**data_dict)
        except TypeError as e:
            raise TypeError(f"Error while constructing {cls.__name__}: {str(e)}") from e

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the instance to a dictionary representation that is compatible with the schema.

        This method recursively converts all properties of the SchemaObject, including nested SchemaObject instances,
        into a dictionary format, following the naming conventions required by the schema. This allows the object
        to be easily serialized into JSON or another dictionary-based format.

        Note that it does not discriminate between properties defined in the schema and any that are dynamically added
        afterwards. This method does not therefore guarantee that the output conforms to the schema.

        Returns:
            Dict[str, Any]: A dictionary representation of the SchemaObject instance, with property names converted
                            to PascalCase to align with the schema.
        """
        result = {}
        for prop_name, value in self.__dict__.items():
            if isinstance(value, SchemaObject) or isinstance(value, IdDescriptionEnum):
                result[
                    snake_to_pascal(prop_name, self._special_names_set)
                ] = value.to_dict()
            elif (
                isinstance(value, list) and value and isinstance(value[0], SchemaObject)
            ):
                result[snake_to_pascal(prop_name, self._special_names_set)] = [
                    item.to_dict() for item in value
                ]
            else:
                result[snake_to_pascal(prop_name, self._special_names_set)] = value
        return result

    def to_json(self, path_or_file: Union[str, os.PathLike, TextIO]) -> None:
        """
        Serializes the instance to a JSON file or stream.

        This method saves the dictionary representation of the SchemaObject instance to a JSON file
        or a file-like object.

        Note that it does not discriminate between properties defined in the schema and any that are dynamically added
        afterwards. This method does not therefore guarantee that the output conforms to the schema.

        Args:
            path_or_file (Union[str, os.PathLike, TextIO]): The file path or file-like object where the JSON
                                                            should be saved. If a string or os.PathLike is provided,
                                                            it is treated as a file path. If a file-like object is
                                                            provided, the JSON is written directly to it.

        Returns:
            None

        Raises:
            IOError: If an error occurs during file writing.
            TypeError: If an object within the SchemaObject cannot be serialized using the default JSON encoder
                       or the custom serializer (`json_serializer`).
        """
        if isinstance(path_or_file, (str, os.PathLike)):
            with open(path_or_file, "w") as file:
                json.dump(
                    self.to_dict(),
                    file,
                    indent=2,
                    default=convert_non_json_serializable_types,
                )
        else:
            json.dump(
                self.to_dict(),
                path_or_file,
                indent=2,
                default=convert_non_json_serializable_types,
            )


class IdDescriptionEnum(Enum):
    """
    An enumeration class for items with an ID and a description.

    Each member of this enum has an ID and a description. This class
    provides methods to convert between dictionaries and enum members.

    Attributes:
        id (str): The unique identifier for the enum member.
        description (str): A descriptive text for the enum member.
    """

    def __init__(self, id, description):
        """
        Initializes an enum member with an ID and a description.

        Args:
            id (str): The unique identifier for the enum member.
            description (str): A descriptive text for the enum member.
        """
        self.id = id
        self.description = description

    @classmethod
    def from_dict(cls, data_dict):
        """
        Creates an enum member from a dictionary.

        Args:
            data_dict (dict): A dictionary with keys 'Id' and 'Description'.

        Returns:
            IdDescriptionEnum: The matching enum member.

        Raises:
            ValueError: If no matching enum member is found.
        """
        for member in cls:
            if member.id == data_dict["Id"]:
                return member
        raise ValueError("No matching {cls.__name__} enum found")

    def to_dict(self):
        """
        Converts the enum member to a dictionary.

        Returns:
            dict: A dictionary with keys 'Id' and 'Description' representing the enum member.
        """
        return {"Id": self.id, "Description": self.description}
