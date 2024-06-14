# TA Data Kit (tadatakit)

TA Data Kit is a Python library developed by [TA Instruments&trade;](https://www.tainstruments.com/), designed for easy parsing and handling of data exported by [TRIOS&trade; JSON Export Feature](https://www.tainstruments.com/trios-software/#data).

## Examples

If you would like to jump to some usage examples head over to our [collection of Jupyter Notebooks](examples/README.md) showing everything from data reading, plotting, analysis, data conversion and more.

## Installation

### Prerequisites

Before installing `tadatakit`, ensure that you have Python 3.9 or later installed on your system. You can download Python from the official [Python website](https://www.python.org/downloads/).

### Installing via Pip

Open your terminal or command prompt and run the following command:

```bash
pip install tadatakit
```

## Features

The `tadatakit` library offers a robust suite of features designed to simplify and enhance the way you handle data from TRIOS JSON Export Feature.

- **Dynamic Class Generation:** Automatically generates Python classes from the [TRIOS JSON Schema](https://software.tainstruments.com/schemas/TRIOSJSONExportSchema). This ensures that the data models are always in sync with the latest schema definitions.

- **Pandas Integration:** Seamlessly converts data into [pandas](https://pandas.pydata.org/) DataFrames, making it easier to perform complex data analysis, visualization, and manipulation directly from experiment results.

- **Extensible Architecture:** Designed with flexibility in mind, allowing users to easily extend or customize the generated classes to suit specific needs. Whether adding new methods, integrating with other libraries, or modifying property behaviors, `tadatakit` supports it all.

- **Type-Safe Operations:** Employs Python type hints throughout the dynamically generated classes, which enhances code quality and reliability through static type checking.

- **Serialization and Deserialization:** Includes built-in methods for JSON serialization and deserialization, facilitating easy data storage and retrieval, and ensuring data integrity across different stages of data handling.

- **Schema-Driven Validation:** Automatically validates data against the schema upon loading, ensuring that the data conforms to the expected structure and types defined by TA Instruments.

## Quick Start

### Classes

To utilize classes like `Experiment`, import them directly from the `tadatakit.classes` module. These classes are dynamically generated based on the data schema, with helper functions added.

Explore the `Experiment` class in a REPL environment (iPython or Jupyter Notebook):

```python
from tadatakit.classes import Experiment

Experiment?
```

### File Parsing

Easily parse files using the `from_json` method on the `Experiment` class, as demonstrated below:

```python
from tadatakit.classes import Experiment

experiment = Experiment.from_json("<path/to/json_file.json>")
```

As files can be large, be aware that this can take a large amount of memory.

### Using The Data

`Experiment` includes a convenience function to return the results data as a [pandas](https://pandas.pydata.org/) DataFrame. The example below demonstrates parsing a file and utilizing the DataFrame:

```python
from tadatakit.classes import Experiment

experiment = Experiment.from_json("<path/to/json_file.json>")
df = experiment.get_dataframe()
```

## Utilizing and Extending Classes in TA Data Kit

The `tadatakit` library offers a versatile framework for handling and manipulating data through dynamically generated classes. These classes can be used directly (1), extended with additional functionality (2), or fully customized (3).

### 1. Using Auto-Generated Classes

Classes such as `Experiment` are dynamically created from a JSON schema by the `class_generator` module. They come equipped with all necessary properties and methods for basic data handling:

```python
from tadatakit.class_generator import Experiment

experiment = Experiment.from_json('experiment_data.json')

print(experiment.start_time)
```

### 2. Using Auto-Generated Classes Extended With Helper Functions

Use `Experiment` imported from the `classes` module to take advantage of helper functions like:

- **`get_dataframe`**: Transforms `Experiment` results into a pandas DataFrame.
- **`get_dataframes_by_step`**: Divides results into multiple DataFrames, one per procedure step.

**Usage Example:**

```python
from tadatakit.classes import Experiment

experiment = Experiment.from_json('path_to_data.json')
df = experiment.get_dataframe()
print(df.head(5))

step, dfs = experiment.get_dataframes_by_step()
for step, df in zip(step, dfs):
    print(step)
    print(df.head(5))
```

### 3. Building Custom Extensions

Create custom functionality by adding new methods or altering existing behaviors, perhaps to add polars support, an analysis pipeline, or methods for injection into databases or LIMS systems:

**Steps to Extend:**

1. **Define New Functions**: Craft functions that fulfill specific requirements.
2. **Attach to Classes**: Dynamically bind these functions to the classes.
3. **Implement in Workflow**: Integrate these enhanced objects into your application.

**Custom Method Example:**

```python
from tadatakit.class_generator import Experiment
import datetime

def time_since_experiment(self):
    return datetime.datetime.now() - self.start_time

setattr(Experiment, "time_since_experiment", time_since_experiment)

experiment = Experiment.from_json('data.json')
print(experiment.time_since_experiment())
```

> Note: we provide no guarantee that your functions will not conflict with future additions to the schema. For example, if you add a dynamic property of `Experiment.end_time` it may conflict in the future with an `EndTime` property in the schema.

## Explanation Of Approach

The `tadatakit.class_generator` module within the TA Data Kit automates the creation of Python classes directly from the TA Instruments TRIOS JSON Export Schema. This process allows for dynamic and efficient handling of data that conforms to defined standards, enhancing both development speed and data integrity. Here’s how the library achieves this:

### Overview
The library converts a JSON schema provided in a specification file into fully functional Python classes. These classes include type hints, serialization methods, and custom behaviors, closely mirroring the structure and requirements laid out in the schema.

### Steps for Class Generation
#### 1. Schema Loading
The process begins with loading the JSON schema. This schema defines the structure, types, required fields, and additional validation rules for the data.

#### 2. Schema Parsing
The loaded schema is parsed to identify different data structures and types. This includes simple types like strings and numbers, complex objects, arrays, and special formats like dates and UUIDs.

#### 3. Class Creation
For each definition in the schema (representing a potential data model), a Python class is dynamically generated. The library maps JSON types to Python types (e.g., `integer` to `int`, `object` to custom classes) and integrates any constraints and nested structures as class attributes.

#### 4. Property Handling
Each class is equipped with properties based on the schema's definitions. Properties are added dynamically with appropriate getters, setters, and deletions to manage data access and ensure type safety. In some places, for example results data, the schema allows for `additionalProperties` which are treated as `kwargs` in Python.

#### 5. Method Integration
Serialization and deserialization methods such as `from_json`, `to_json`, `from_dict`, and `to_dict` are integrated into each class. These methods handle conversion between JSON strings, dictionaries, and class instances, facilitating easy data exchange and storage operations.

#### 6. Inheritance and Composition
If the schema specifies inheritance (using `allOf`) or composition (using `anyOf` or `oneOf`), the library constructs classes that inherit from multiple bases or handle multiple data types, ensuring that the generated classes faithfully represent the schema's intended data structures.

#### 7. Registration and Accessibility
Generated classes are registered in a global class registry within the library. This registry allows for easy retrieval and instantiation of classes based on schema names, supporting dynamic access and manipulation of data in a type-safe manner.

## Contributing

We welcome contributions from the community and are pleased to have you join us in improving `tadatakit`. Whether you are fixing bugs, adding new features, improving documentation, or suggesting new functionality, your input is valuable!

If you are interested in contributing to the `tadatakit` library, please read our [contributing guidelines](CONTRIBUTING.md) for detailed information on how to get started, coding conventions, and the pull request process.

## Notes

TA Instruments, TA, and TRIOS are trademarks of Waters Technologies Corporation.