from datetime import datetime
import dateutil
from uuid import UUID
from typing import Any, Type, Union, TextIO, Dict
import inspect
from functools import wraps
import json
import os

from .utils import (
    type_hint_to_str,
    is_instance,
    snake_to_pascal,
    pascal_to_snake,
    json_serializer,
)

native_type_mapping = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}

native_format_mapping = {
    "date-time": datetime,
    "uuid": UUID,
    "byte": bytes,  # For base64 encoded data
}


class SchemaObject:
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

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._added_properties = {}
        cls._doc_string_base = f"A TA Instruments `{cls.__name__}` object.\n\nArgs:"
        cls._kwargs_property = None
        cls._update_init()

    # TODO: Clean docstrings?

    @classmethod
    def add_property(
        cls,
        name: str,
        caster: Any,
        type_hint: Type,
        default: Any = inspect.Parameter.empty,
    ):
        cls._added_properties[name] = {
            "caster": caster,
            "type_hint": type_hint,
            "default": default,
        }
        cls._update_init()

    @classmethod
    def add_additional_properties(cls, caster: Any = None, type_hint: Type = Any):
        if type_hint is None:
            type_hint = Any
        cls._kwargs_property = {
            "caster": caster,
            "type_hint": type_hint,
        }
        cls._update_init()

    @classmethod
    def _update_init(cls):
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
                                value = dateutil.parser.parse(value)
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
                                value = dateutil.parser.parse(value)
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
        Combine __init__ methods from multiple inheritance dynamically.

        This method constructs a new __init__ method that integrates __init__ methods from all parent classes,
        handling properties and kwargs appropriately. It ensures that all parent initializations are respected.
        """
        parameters = [
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        doc_string = cls._doc_string_base
        annotations = {}
        added_properties = {}

        for supercls in cls.__mro__[1:-2]:
            if supercls._added_properties is not None:
                for name, property_details in supercls._added_properties.items():
                    param_kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
                    parameters.append(
                        inspect.Parameter(
                            name, param_kind, default=property_details["default"]
                        )
                    )
                    annotations[name] = property_details["type_hint"]
                    type_hint_str = type_hint_to_str(property_details["type_hint"])
                    doc_string += f"\n    {name} ({type_hint_str})"
                added_properties.update(supercls._added_properties)

        for supercls in cls.__mro__[1:-2]:
            if supercls._kwargs_property is not None:
                annotations["kwargs"] = supercls._kwargs_property["type_hint"]
                type_hint_str = type_hint_to_str(supercls._kwargs_property["type_hint"])
                doc_string += f"\n    **kwargs: Dict[str, {type_hint_str}] (optional)"
                parameters.append(
                    inspect.Parameter("kwargs", inspect.Parameter.VAR_KEYWORD)
                )
                cls._kwargs_property = supercls._kwargs_property

        cls._added_properties = added_properties
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

        replacement_init_function.__annotations__ = annotations
        cls.__init__ = replacement_init_function
        cls.__init__.__signature__ = new_sig
        cls.__init__.__doc__ = doc_string

    @classmethod
    def from_json(cls, path_or_file: Union[str, os.PathLike, TextIO]) -> "SchemaObject":
        """
        Initialize an instance of the class from a JSON file or file-like object.

        Args:
            path_or_file (Union[str, os.PathLike, TextIO]): Path to the JSON input file or a file-like object.

        Returns:
            SchemaObject: An instance of the class initialized with data from the JSON input.
        """
        if isinstance(path_or_file, (str, os.PathLike)):
            with open(path_or_file, "r") as file:
                data = json.load(file)
        else:
            data = json.load(path_or_file)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data_dict: dict) -> "SchemaObject":
        """
        Recursive method to instantiate objects from a dictionary.

        Args:
            data_dict (dict): The dictionary containing data to instantiate the object.

        Returns:
            SchemaObject: An instance of the class initialized with data from the dictionary.

        Raises:
            TypeError: If a required argument is missing or if there is a type mismatch.
        """
        data_dict = {pascal_to_snake(k): v for k, v in data_dict.items()}
        try:
            return cls(**data_dict)
        except TypeError as e:
            raise TypeError(f"Error while constructing {cls.__name__}: {str(e)}") from e

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
