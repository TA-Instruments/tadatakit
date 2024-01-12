from .abstract_class import Algorithm, add_input, add_output, store_inputs
import numpy as np
from numpy.typing import ArrayLike
from typing import Dict, Tuple


class LinearRegression(Algorithm):
    """Linear Regression algorithm for fitting a line to a set of points.

    This class inherits from the Algorithm base class and implements methods for
    executing linear regression on a set of data points.

    Attributes:
        x (ArrayLike): Input feature array.
        y (ArrayLike): Output/target array.
        m (float): Slope of the fitted line (output).
        c (float): Y-intercept of the fitted line (output).

    Example:
        >>> import numpy as np
        >>> x = np.array([1, 2, 3, 4, 5])
        >>> y = np.array([2, 4, 5, 4, 5])
        >>> lr = LinearRegression()
        >>> lr.execute(x, y)
        {'m': 0.6000000000000001, 'c': 2.199999999999999}
        >>> lr.predict(np.array([6, 7]))
        array([5.8, 6.4])
        >>> lr.render()
        (array([1, 5]), array([2.8, 5.2]))
        >>> lr.summary
        {'inputs': {'x': array([1, 2, 3, 4, 5]), 'y': array([2, 4, 5, 4, 5])},
        'outputs': {'slope': 0.6000000000000001, 'intercept': 2.199999999999999},
        'config': {}}
    """

    x = add_input("x")
    y = add_input("y")

    slope = add_output("slope")
    intercept = add_output("intercept")

    def __init__(self):
        super().__init__()

    @store_inputs
    def execute(self, x: ArrayLike, y: ArrayLike) -> Dict[str, float]:
        """Performs linear regression on input data.

        Uses the ordinary least squares method to fit a line to the input data points.

        Args:
            x (ArrayLike): Input feature array.
            y (ArrayLike): Output/target array.

        Returns:
            Dict[str, float]: Outputs of the linear regression, including slope and intercept.

        Raises:
            ValueError: If the linear regression calculation fails due to linear algebra errors.
        """
        try:
            A = np.vstack([x, np.ones(len(x))]).T
            self.slope, self.intercept = np.linalg.lstsq(A, y, rcond=None)[0]
        except np.linalg.LinAlgError as e:
            raise ValueError("Linear regression calculation failed") from e
        return self.outputs

    def predict(self, x: ArrayLike) -> ArrayLike:
        """Predicts the output for given input features using the fitted line.

        Args:
            x (ArrayLike): Input features array for which the output is to be predicted.

        Returns:
            ArrayLike: Predicted output array.
        """
        return self.slope * x + self.intercept

    def render(self) -> Tuple[ArrayLike, ArrayLike]:
        """Generates endpoints for plotting the fitted line.

        Returns:
            Tuple[ArrayLike, ArrayLike]: A tuple containing the endpoints of the x and y values.
        """
        endpoints = np.array([self.x.min(), self.x.max()])
        return endpoints, self.predict(endpoints)
