# TA Data Kit (tadatakit)

TA Data Kit is a Python library developed by [TA Instruments](https://www.tainstruments.com/), designed for efficient data parsing, visualization, and analysis in the field of materials characterization.

## Installation

...

## Features

* **Data Parsing**: Efficiently parse data from various file formats.
* **Data Visualization**: Create insightful visualizations to understand complex data sets.
* **Data Analysis**: Advanced analytical tools tailored for materials characterization.

## Quick Start

### Classes

Importing the `Experiment` class dynamically generates classes for the entire data schema.

Try running the following in a REPL (iPython or Jupyter Notebook):

```python
from tadatakit.classes import Experiment

Experiment?
```

### File Parsing

A file can be parsed using the `from_json` method on the `Experiment` class, as below.

```python
from tadatakit.classes import Experiment

experiment = Experiment.from_json("<path/to/json_file.json>")
```

### Using The Data

A convenience function is implemented to provide a pandas DataFrame at `Experiment.dataframe`. The below example shows the parsing of a file and the use of that dataframe.

```python
from tadatakit.classes import Experiment

experiment = Experiment.from_json("<path/to/json_file.json>")
experiment.dataframe.head()
```


## Documentation

...

## Contributing

...

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments
...

## Contact
For questions and feedback, please reach out to [TA Instruments Support](mailto:tainstruments@waters.com).