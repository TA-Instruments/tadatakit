# Contributing to TA Data Kit
We're excited that you're interested in contributing to TA Data Kit! This document provides guidelines and instructions to help you contribute effectively. Please take a moment to read through this document before submitting contributions.

## Getting Started

### Prerequisites

Before you begin, you'll need to have the following installed:

* Git
* Python
* [Poetry](https://python-poetry.org/docs/#installation)

## Setting Up the Project

1. Clone the Repository

    * Clone the project repository to your local machine using:
    ```bash
    git clone git@github.com:TA-Instruments/tadatakit.git
    ```
    * Navigate into the project directory:
    ```bash
    cd tadatakit
    ```
2. Install Dependencies
   
   * Use Poetry to install the project dependencies:
   ```bash
   poetry install
   ```


## Pre-commit Hooks

To ensure code quality and consistency, we use pre-commit hooks. These hooks automatically check for issues like code formatting, linting errors, and more before you commit.

### Installing Pre-commit Hooks
* After setting up the project, install the pre-commit hooks by running:
```bash
poetry run pre-commit install
```
This command sets up the necessary Git hooks.

## Making Changes and Committing
1. **Make Your Changes**
    * Work on the project as you normally would.

2. **Stage Your Changes**
    * Once you're ready to commit, stage your changes using Git:
    ```bash
    git add [file_name]
    ```
    or stage all changes with:
    ```bash
    git add .
    ```

3. Commit Your Changes
   * Commit your changes with a meaningful commit message:
    ```bash
    git commit -m "Your descriptive commit message"
    ```
    The pre-commit hooks will run automatically. If there are no issues, your commit will be processed.

4. Handling Hook Failures
    * If a hook fails, it will output the reason for the failure.
    * Address the reported issues, stage the changes again, and try committing.

## Pull Requests
When you're ready to submit your changes, create a pull request:

1. Push your changes to a branch in your fork of the repository.
2. Open a pull request in the TA Data Kit repository.
3. Provide a clear description of the changes in the pull request description.

## Code Review Process
Our team will review your pull request and provide feedback or merge it.

## Questions or Issues?
If you have questions or encounter any issues, please open an issue in the repository, and we'll do our best to address it.

Thank you for contributing to TA Data Kit!

