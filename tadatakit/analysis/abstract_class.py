from functools import wraps
from inspect import Signature, signature
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict


def store_inputs(f: Callable) -> Callable:
    """Decorator to store function arguments in the 'inputs' attribute of a class.

    Args:
        f (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function with input storage capability.
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        sig: Signature = signature(f)
        param_names = list(sig.parameters.keys())[1:]  # Skip 'self'
        self.inputs = {name: arg for name, arg in zip(param_names, args)}
        self.inputs.update(kwargs)
        return f(self, *args, **kwargs)

    return wrapper


def add_registry_property(key, registry_name):
    """Creates a property that is stored in a specific registry within an object.

    Args:
        key (str): The key under which the property is stored in the registry.
        registry_name (str): The name of the registry attribute.

    Returns:
        property: A property object with getter and setter for the specified key.
    """

    def getter(self):
        return self.__dict__.get(registry_name, {}).get(key)

    def setter(self, value):
        self.__dict__.setdefault(registry_name, {})[key] = value

    return property(getter, setter)


def add_configuration(key):
    """Shortcut for adding a property stored in the 'config' registry.

    Args:
        key (str): The key under which the property is stored in the config.

    Returns:
        property: A property object for the specified key in the config registry.
    """
    return add_registry_property(key, "config")


def add_input(key):
    """Shortcut for adding a property stored in the 'inputs' registry.

    Args:
        key (str): The key under which the property is stored in the inputs.

    Returns:
        property: A property object for the specified key in the inputs registry.
    """
    return add_registry_property(key, "inputs")


def add_output(key):
    """Shortcut for adding a property stored in the 'outputs' registry.

    Args:
        key (str): The key under which the property is stored in the outputs.

    Returns:
        property: A property object for the specified key in the outputs registry.
    """
    return add_registry_property(key, "outputs")


class Algorithm(ABC):
    """Abstract base class for algorithm implementations.

    This class provides a structure for algorithm classes with inputs, outputs,
    and configuration. Subclasses should implement the execute method.

    Attributes:
        inputs (Dict[str, Any]): Dictionary to store input parameters.
        outputs (Dict[str, Any]): Dictionary to store output parameters.
        config (Dict[str, Any]): Dictionary to store configuration parameters.

    Example:
        Below is an example of a simple LinearRegression algorithm implementation using the Algorithm class.

        ```python
        from .abstract_classes import Algorithm, add_input, add_output, store_inputs
        import numpy as np

        class LinearRegression(Algorithm):
            x = add_input("x")
            y = add_input("y")

            slope = add_output("slope")
            intercept = add_output("intercept")

            @store_inputs
            def execute(self, x, y):
                A = np.vstack([x, np.ones(len(x))]).T
                self.slope, self.intercept = np.linalg.lstsq(A, y, rcond=None)[0]

        # Usage
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([2, 4, 5, 4, 5])
        lr = LinearRegression()
        lr.execute(x, y)
        print("Slope:", lr.slope, "Intercept:", lr.intercept)
        ```
    """

    def __init__(self):
        """Initializes an Algorithm instance with empty inputs, outputs, and config."""
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}

    @property
    def summary(self) -> Dict[str, Dict[str, Any]]:
        """Summarizes the current state of the algorithm.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary containing the inputs, outputs, and configuration of the algorithm.
        """
        return {"inputs": self.inputs, "outputs": self.outputs, "config": self.config}

    @abstractmethod
    def execute(self):
        """Abstract method to execute the algorithm. Must be implemented by subclasses."""
        pass
