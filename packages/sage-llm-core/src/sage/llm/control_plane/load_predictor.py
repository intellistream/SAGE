# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Load predictor for forecasting future request patterns.

Supports multiple prediction strategies:
- Constant: Assumes next load equals current load
- Moving Average: Uses sliding window average
- ARIMA: Time series with trends and seasonality (optional)
- Prophet: Facebook's Prophet for complex patterns (optional)

Ported from Dynamo Planner load_predictor.py.
"""

import logging
from abc import ABC, abstractmethod
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class BaseLoadPredictor(ABC):
    """Base class for load predictors."""

    def __init__(self, window_size: int = 10):
        """
        Initialize the load predictor.

        Args:
            window_size: Number of historical data points to keep
        """
        self.window_size = window_size
        self.num_requests_history = deque(maxlen=window_size)
        self.isl_history = deque(maxlen=window_size)  # Input Sequence Length
        self.osl_history = deque(maxlen=window_size)  # Output Sequence Length

    def add_data_point(
        self,
        num_requests: float,
        avg_isl: float,
        avg_osl: float,
    ):
        """
        Add an observed data point to the history.

        Args:
            num_requests: Number of requests in the interval
            avg_isl: Average input sequence length
            avg_osl: Average output sequence length
        """
        self.num_requests_history.append(num_requests)
        self.isl_history.append(avg_isl)
        self.osl_history.append(avg_osl)

    @abstractmethod
    def predict(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Predict the next interval's load.

        Returns:
            Tuple of (predicted_num_requests, predicted_isl, predicted_osl)
            Returns (None, None, None) if insufficient data
        """
        pass

    def has_sufficient_data(self, min_points: int = 1) -> bool:
        """Check if we have sufficient data for prediction."""
        return len(self.num_requests_history) >= min_points

    def get_history_size(self) -> int:
        """Get the number of historical data points."""
        return len(self.num_requests_history)


class ConstantPredictor(BaseLoadPredictor):
    """
    Constant predictor - assumes next load equals current load.

    Best for: Stable workloads with minimal variation.
    """

    def predict(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Return the most recent observation as prediction."""
        if not self.has_sufficient_data():
            logger.debug("Insufficient data for constant prediction")
            return None, None, None

        prediction = (
            self.num_requests_history[-1],
            self.isl_history[-1],
            self.osl_history[-1],
        )

        logger.debug(
            f"Constant prediction: req={prediction[0]:.1f}, "
            f"isl={prediction[1]:.1f}, osl={prediction[2]:.1f}"
        )

        return prediction


class MovingAveragePredictor(BaseLoadPredictor):
    """
    Moving average predictor - uses sliding window average.

    Best for: Smoothing out short-term fluctuations.
    """

    def predict(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Return the average of recent observations."""
        if not self.has_sufficient_data():
            logger.debug("Insufficient data for moving average prediction")
            return None, None, None

        num_req = sum(self.num_requests_history) / len(self.num_requests_history)
        isl = sum(self.isl_history) / len(self.isl_history)
        osl = sum(self.osl_history) / len(self.osl_history)

        logger.debug(f"Moving average prediction: req={num_req:.1f}, isl={isl:.1f}, osl={osl:.1f}")

        return num_req, isl, osl


class ExponentialSmoothingPredictor(BaseLoadPredictor):
    """
    Exponential smoothing predictor - gives more weight to recent observations.

    Best for: Workloads with gradual trends.
    """

    def __init__(self, window_size: int = 10, alpha: float = 0.3):
        """
        Initialize with smoothing parameter.

        Args:
            window_size: Number of historical data points
            alpha: Smoothing factor (0-1). Higher = more weight to recent data
        """
        super().__init__(window_size)
        self.alpha = alpha

    def predict(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Apply exponential smoothing to predict next value."""
        if not self.has_sufficient_data():
            return None, None, None

        def smooth(values):
            if len(values) == 1:
                return values[0]

            smoothed = values[0]
            for value in values[1:]:
                smoothed = self.alpha * value + (1 - self.alpha) * smoothed
            return smoothed

        num_req = smooth(list(self.num_requests_history))
        isl = smooth(list(self.isl_history))
        osl = smooth(list(self.osl_history))

        logger.debug(
            f"Exponential smoothing prediction (alpha={self.alpha}): "
            f"req={num_req:.1f}, isl={isl:.1f}, osl={osl:.1f}"
        )

        return num_req, isl, osl


class ARIMAPredictor(BaseLoadPredictor):
    """
    ARIMA predictor - Auto-Regressive Integrated Moving Average.

    Best for: Time series with trends and seasonality.
    Requires: statsmodels library
    """

    def __init__(self, window_size: int = 10):
        super().__init__(window_size)
        self._arima_available = False
        try:
            from statsmodels.tsa.arima.model import ARIMA  # noqa: F401

            self._arima_available = True
            logger.info("ARIMA predictor available")
        except ImportError:
            logger.warning(
                "statsmodels not available, ARIMA predictor will fall back to moving average"
            )

    def predict(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Use ARIMA to predict next value, or fall back to moving average."""
        if not self.has_sufficient_data(min_points=5):
            return None, None, None

        if not self._arima_available:
            # Fall back to moving average
            fallback = MovingAveragePredictor(self.window_size)
            fallback.num_requests_history = self.num_requests_history.copy()
            fallback.isl_history = self.isl_history.copy()
            fallback.osl_history = self.osl_history.copy()
            return fallback.predict()

        try:
            from statsmodels.tsa.arima.model import ARIMA

            def fit_and_forecast(values):
                # Use simple ARIMA(1,1,1) as default
                model = ARIMA(list(values), order=(1, 1, 1))
                fitted = model.fit()
                forecast = fitted.forecast(steps=1)
                return forecast[0]

            num_req = fit_and_forecast(self.num_requests_history)
            isl = fit_and_forecast(self.isl_history)
            osl = fit_and_forecast(self.osl_history)

            logger.debug(f"ARIMA prediction: req={num_req:.1f}, isl={isl:.1f}, osl={osl:.1f}")

            return num_req, isl, osl

        except Exception as e:
            logger.warning(f"ARIMA prediction failed: {e}, using moving average")
            fallback = MovingAveragePredictor(self.window_size)
            fallback.num_requests_history = self.num_requests_history.copy()
            fallback.isl_history = self.isl_history.copy()
            fallback.osl_history = self.osl_history.copy()
            return fallback.predict()


class ProphetPredictor(BaseLoadPredictor):
    """
    Prophet predictor - Facebook's Prophet for time series forecasting.

    Best for: Complex seasonal patterns and trend changes.
    Requires: prophet library
    """

    def __init__(self, window_size: int = 10):
        super().__init__(window_size)
        self._prophet_available = False
        try:
            from prophet import Prophet  # noqa: F401

            self._prophet_available = True
            logger.info("Prophet predictor available")
        except ImportError:
            logger.warning(
                "prophet not available, Prophet predictor will fall back to moving average"
            )

    def predict(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Use Prophet to predict next value, or fall back to moving average."""
        if not self.has_sufficient_data(min_points=10):
            return None, None, None

        if not self._prophet_available:
            # Fall back to moving average
            fallback = MovingAveragePredictor(self.window_size)
            fallback.num_requests_history = self.num_requests_history.copy()
            fallback.isl_history = self.isl_history.copy()
            fallback.osl_history = self.osl_history.copy()
            return fallback.predict()

        try:
            import pandas as pd
            from prophet import Prophet

            def fit_and_forecast(values):
                # Create dataframe with timestamp and values
                df = pd.DataFrame(
                    {
                        "ds": pd.date_range(start="2024-01-01", periods=len(values), freq="H"),
                        "y": list(values),
                    }
                )

                # Fit Prophet model
                model = Prophet(
                    daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=False
                )
                model.fit(df)

                # Forecast next period
                future = model.make_future_dataframe(periods=1, freq="H")
                forecast = model.predict(future)
                return forecast["yhat"].iloc[-1]

            num_req = fit_and_forecast(self.num_requests_history)
            isl = fit_and_forecast(self.isl_history)
            osl = fit_and_forecast(self.osl_history)

            logger.debug(f"Prophet prediction: req={num_req:.1f}, isl={isl:.1f}, osl={osl:.1f}")

            return max(0, num_req), max(0, isl), max(0, osl)

        except Exception as e:
            logger.warning(f"Prophet prediction failed: {e}, using moving average")
            fallback = MovingAveragePredictor(self.window_size)
            fallback.num_requests_history = self.num_requests_history.copy()
            fallback.isl_history = self.isl_history.copy()
            fallback.osl_history = self.osl_history.copy()
            return fallback.predict()


# Predictor registry
LOAD_PREDICTORS = {
    "constant": ConstantPredictor,
    "moving_average": MovingAveragePredictor,
    "exponential_smoothing": ExponentialSmoothingPredictor,
    "arima": ARIMAPredictor,
    "prophet": ProphetPredictor,
}


class LoadPredictor:
    """
    Load predictor factory.

    Creates the appropriate predictor based on type.
    """

    def __new__(
        cls,
        predictor_type: str = "constant",
        window_size: int = 10,
        **kwargs,
    ):
        """
        Create a load predictor instance.

        Args:
            predictor_type: Type of predictor (constant, moving_average, arima, prophet)
            window_size: Number of historical data points
            **kwargs: Additional predictor-specific arguments

        Returns:
            Instance of the requested predictor
        """
        predictor_class = LOAD_PREDICTORS.get(predictor_type)

        if predictor_class is None:
            logger.warning(f"Unknown predictor type '{predictor_type}', using 'constant'")
            predictor_class = ConstantPredictor

        # Check if predictor supports additional kwargs
        if predictor_type == "exponential_smoothing" and "alpha" in kwargs:
            return predictor_class(window_size=window_size, alpha=kwargs["alpha"])
        else:
            return predictor_class(window_size=window_size)
