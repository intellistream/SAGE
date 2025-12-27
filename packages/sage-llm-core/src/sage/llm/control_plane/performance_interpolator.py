# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Performance interpolators for estimating TTFT, ITL, and throughput.

These interpolators use pre-profiling data or online learning to predict
performance characteristics based on workload parameters.

Adapted from Dynamo Planner utils/perf_interpolation.py.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PrefillInterpolator:
    """
    Interpolator for prefill performance metrics.

    Estimates:
    - Time To First Token (TTFT) based on input sequence length
    - Throughput per GPU based on input sequence length
    """

    def __init__(self, profile_data_dir: Optional[str] = None):
        """
        Initialize prefill interpolator.

        Args:
            profile_data_dir: Directory containing pre-profiling data
                            If None, uses simple heuristics or online learning
        """
        self.profile_data_dir = profile_data_dir
        self.use_online_learning = profile_data_dir is None

        if profile_data_dir:
            self._load_profile_data()
        else:
            logger.info("PrefillInterpolator using heuristic model (no profile data)")
            self._init_heuristic_model()

    def _load_profile_data(self):
        """Load pre-profiling data from directory."""
        # TODO: Implement loading from profiling results
        # Format: CSV or JSON with (isl, ttft, throughput) tuples
        logger.warning(f"Profile data loading not yet implemented for {self.profile_data_dir}")
        self._init_heuristic_model()

    def _init_heuristic_model(self):
        """Initialize simple heuristic performance model."""
        # Simple linear model: TTFT = base_latency + isl * token_latency
        self.base_ttft_ms = 50.0  # Base latency
        self.token_latency_ms = 0.1  # Per-token processing time

        # Throughput model: tokens/s/gpu decreases with sequence length
        self.max_throughput_per_gpu = 200.0  # Max tokens/s/gpu at low ISL
        self.throughput_decay_factor = 0.0001  # Decay with ISL

    def interpolate_ttft(self, isl: float) -> float:
        """
        Estimate Time To First Token for given input sequence length.

        Args:
            isl: Input sequence length in tokens

        Returns:
            Estimated TTFT in milliseconds
        """
        if self.use_online_learning:
            # Heuristic model
            ttft = self.base_ttft_ms + isl * self.token_latency_ms
        else:
            # TODO: Use interpolation from profile data
            ttft = self.base_ttft_ms + isl * self.token_latency_ms

        logger.debug(f"Interpolated TTFT for ISL={isl:.0f}: {ttft:.2f}ms")
        return ttft

    def interpolate_thpt_per_gpu(self, isl: float) -> float:
        """
        Estimate throughput per GPU for given input sequence length.

        Args:
            isl: Input sequence length in tokens

        Returns:
            Estimated throughput in tokens/s/gpu
        """
        if self.use_online_learning:
            # Heuristic model: throughput decreases with ISL
            throughput = self.max_throughput_per_gpu * (
                1.0 / (1.0 + self.throughput_decay_factor * isl)
            )
        else:
            # TODO: Use interpolation from profile data
            throughput = self.max_throughput_per_gpu * (
                1.0 / (1.0 + self.throughput_decay_factor * isl)
            )

        logger.debug(
            f"Interpolated prefill throughput for ISL={isl:.0f}: {throughput:.2f} tokens/s/gpu"
        )
        return throughput

    def update_online_model(self, isl: float, observed_ttft: float):
        """
        Update online learning model with observed data.

        Args:
            isl: Input sequence length
            observed_ttft: Observed TTFT in milliseconds
        """
        if not self.use_online_learning:
            return

        # Simple exponential moving average update
        alpha = 0.1
        predicted_ttft = self.interpolate_ttft(isl)
        error = observed_ttft - predicted_ttft

        # Adjust token latency based on error
        if isl > 0:
            self.token_latency_ms = (1 - alpha) * self.token_latency_ms + alpha * (error / isl)

        logger.debug(f"Updated online model: token_latency={self.token_latency_ms:.4f}ms")


class DecodeInterpolator:
    """
    Interpolator for decode performance metrics.

    Estimates:
    - Inter-Token Latency (ITL) based on concurrency and context length
    - Throughput per GPU based on ITL target and context length
    """

    def __init__(self, profile_data_dir: Optional[str] = None):
        """
        Initialize decode interpolator.

        Args:
            profile_data_dir: Directory containing pre-profiling data
                            If None, uses simple heuristics or online learning
        """
        self.profile_data_dir = profile_data_dir
        self.use_online_learning = profile_data_dir is None

        if profile_data_dir:
            self._load_profile_data()
        else:
            logger.info("DecodeInterpolator using heuristic model (no profile data)")
            self._init_heuristic_model()

    def _load_profile_data(self):
        """Load pre-profiling data from directory."""
        # TODO: Implement loading from profiling results
        logger.warning(f"Profile data loading not yet implemented for {self.profile_data_dir}")
        self._init_heuristic_model()

    def _init_heuristic_model(self):
        """Initialize simple heuristic performance model."""
        # ITL model: base_latency + concurrency_factor * concurrency + context_factor * context
        self.base_itl_ms = 20.0  # Base ITL
        self.concurrency_factor = 2.0  # ITL increase per concurrent request
        self.context_factor = 0.01  # ITL increase per context token

        # Throughput model
        self.max_throughput_per_gpu = 100.0  # Max tokens/s/gpu

    def interpolate_itl(self, concurrency: float, context_length: float) -> float:
        """
        Estimate Inter-Token Latency for given workload.

        Args:
            concurrency: Number of concurrent requests per instance
            context_length: Average context length (ISL + OSL/2)

        Returns:
            Estimated ITL in milliseconds
        """
        if self.use_online_learning:
            # Heuristic model
            itl = (
                self.base_itl_ms
                + self.concurrency_factor * concurrency
                + self.context_factor * context_length
            )
        else:
            # TODO: Use interpolation from profile data
            itl = (
                self.base_itl_ms
                + self.concurrency_factor * concurrency
                + self.context_factor * context_length
            )

        logger.debug(
            f"Interpolated ITL for concurrency={concurrency:.1f}, "
            f"context={context_length:.0f}: {itl:.2f}ms"
        )
        return itl

    def find_best_throughput_per_gpu(
        self, itl: float, context_length: float
    ) -> tuple[float, float, float]:
        """
        Find maximum throughput per GPU that achieves target ITL.

        This is the reverse of interpolate_itl - given target ITL,
        find the maximum sustainable concurrency and resulting throughput.

        Args:
            itl: Target ITL in milliseconds
            context_length: Average context length

        Returns:
            Tuple of (throughput_per_gpu, actual_itl, concurrency)
            - throughput_per_gpu: tokens/s/gpu
            - actual_itl: ITL that would be achieved
            - concurrency: Maximum concurrent requests
        """
        if self.use_online_learning:
            # Solve for concurrency: itl = base + concurrency_factor * c + context_factor * ctx
            # c = (itl - base - context_factor * ctx) / concurrency_factor
            max_concurrency = max(
                0,
                (itl - self.base_itl_ms - self.context_factor * context_length)
                / self.concurrency_factor,
            )

            # Throughput = concurrency * tokens_per_request_per_sec
            # Assume average generation rate based on ITL
            tokens_per_sec_per_request = 1000.0 / itl  # Convert ms to s
            throughput = max_concurrency * tokens_per_sec_per_request

            # Cap at max throughput
            throughput = min(throughput, self.max_throughput_per_gpu)

            # Recalculate actual ITL and concurrency for this throughput
            actual_concurrency = throughput / tokens_per_sec_per_request
            actual_itl = self.interpolate_itl(actual_concurrency, context_length)

        else:
            # TODO: Use reverse interpolation from profile data
            max_concurrency = (
                itl - self.base_itl_ms - self.context_factor * context_length
            ) / self.concurrency_factor
            tokens_per_sec_per_request = 1000.0 / itl
            throughput = min(
                max_concurrency * tokens_per_sec_per_request,
                self.max_throughput_per_gpu,
            )
            actual_concurrency = throughput / tokens_per_sec_per_request
            actual_itl = self.interpolate_itl(actual_concurrency, context_length)

        logger.debug(
            f"Best throughput for ITL={itl:.2f}ms, context={context_length:.0f}: "
            f"{throughput:.2f} tokens/s/gpu (concurrency={actual_concurrency:.1f}, "
            f"actual_itl={actual_itl:.2f}ms)"
        )

        return throughput, actual_itl, actual_concurrency

    def update_online_model(self, concurrency: float, context_length: float, observed_itl: float):
        """
        Update online learning model with observed data.

        Args:
            concurrency: Observed concurrency
            context_length: Observed context length
            observed_itl: Observed ITL in milliseconds
        """
        if not self.use_online_learning:
            return

        # Simple exponential moving average update
        alpha = 0.1
        predicted_itl = self.interpolate_itl(concurrency, context_length)
        error = observed_itl - predicted_itl

        # Adjust concurrency factor based on error
        if concurrency > 0:
            self.concurrency_factor = (1 - alpha) * self.concurrency_factor + alpha * (
                error / concurrency
            )

        logger.debug(f"Updated online model: concurrency_factor={self.concurrency_factor:.4f}")
