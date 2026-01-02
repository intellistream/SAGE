# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Autoscaler - SLA-based dynamic scaling for Prefill/Decode instances.

Ported from Dynamo Planner with adaptations for sageLLM Control Plane.
"""

import asyncio
import logging
import math
import time
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class AutoscalerConfig:
    """Configuration for the Autoscaler."""

    # SLA targets
    target_ttft_ms: float = 200.0  # Target Time To First Token
    target_itl_ms: float = 50.0  # Target Inter-Token Latency

    # Scaling parameters
    adjustment_interval_sec: int = 60  # How often to adjust
    min_prefill_instances: int = 1
    max_prefill_instances: int = 10
    min_decode_instances: int = 1
    max_decode_instances: int = 20

    # GPU budget
    max_gpu_budget: int = 32
    prefill_gpus_per_instance: int = 4
    decode_gpus_per_instance: int = 1

    # Load prediction
    load_predictor_type: str = "constant"  # constant, moving_average, arima, prophet
    prediction_window_size: int = 10

    # Performance interpolation
    profile_data_dir: Optional[str] = None
    enable_online_learning: bool = True

    # Correction factors
    enable_correction: bool = True

    # Behavior
    no_operation: bool = False  # Dry-run mode


class Autoscaler:
    """
    SLA-based autoscaler for Prefill/Decode instances.

    Monitors system metrics, predicts future load, and dynamically adjusts
    the number of Prefill and Decode instances to meet SLA targets.

    Ported from Dynamo Planner (planner_core.py).
    """

    def __init__(
        self,
        config: AutoscalerConfig,
        metrics_collector,
        executor_callback: Callable,
    ):
        """
        Initialize the Autoscaler.

        Args:
            config: Autoscaler configuration
            metrics_collector: Metrics collector instance
            executor_callback: Async callback to apply scaling decisions
                              Signature: async def callback(decision: ScalingDecision)
        """
        self.config = config
        self.metrics_collector = metrics_collector
        self.executor_callback = executor_callback

        # Load predictor
        from .load_predictor import LoadPredictor

        self.load_predictor = LoadPredictor(
            predictor_type=config.load_predictor_type,
            window_size=config.prediction_window_size,
        )

        # Performance interpolators
        self.prefill_interpolator = None
        self.decode_interpolator = None

        if config.profile_data_dir:
            from .performance_interpolator import (
                DecodeInterpolator,
                PrefillInterpolator,
            )

            self.prefill_interpolator = PrefillInterpolator(config.profile_data_dir)
            self.decode_interpolator = DecodeInterpolator(config.profile_data_dir)
            logger.info(f"Loaded performance profiles from {config.profile_data_dir}")
        elif config.enable_online_learning:
            logger.info("Using online learning for performance estimation")
        else:
            logger.warning("No performance profiles and online learning disabled")

        # Correction factors (actual vs expected performance)
        self.prefill_correction_factor = 1.0
        self.decode_correction_factor = 1.0

        # State
        self.running = False
        self.last_adjustment_time = 0
        self._task = None

        logger.info(
            f"Autoscaler initialized: TTFT target={config.target_ttft_ms}ms, "
            f"ITL target={config.target_itl_ms}ms, "
            f"interval={config.adjustment_interval_sec}s"
        )

    async def start(self):
        """Start the autoscaling loop."""
        if self.running:
            logger.warning("Autoscaler already running")
            return

        self.running = True
        self.last_adjustment_time = time.time()
        self._task = asyncio.create_task(self._autoscaling_loop())
        logger.info("Autoscaler started")

    async def stop(self):
        """Stop the autoscaling loop."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Autoscaler stopped")

    async def _autoscaling_loop(self):
        """Main autoscaling loop - runs every adjustment_interval_sec."""
        while self.running:
            try:
                current_time = time.time()
                elapsed = current_time - self.last_adjustment_time

                if elapsed >= self.config.adjustment_interval_sec:
                    logger.info("Starting autoscaling adjustment cycle")
                    await self._perform_adjustment()
                    self.last_adjustment_time = current_time

                # Sleep for a short interval
                await asyncio.sleep(self.config.adjustment_interval_sec / 10)

            except Exception as e:
                logger.error(f"Error in autoscaling loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Brief pause on error

    async def _perform_adjustment(self):
        """Perform one adjustment cycle."""

        # 1. Collect metrics
        metrics = await self.metrics_collector.collect_metrics()

        if not metrics.is_valid():
            logger.info("Metrics invalid (no active requests), skipping adjustment")
            return

        logger.info(
            f"Observed metrics: requests={metrics.num_requests:.1f}, "
            f"isl={metrics.avg_isl:.1f}, osl={metrics.avg_osl:.1f}, "
            f"ttft={metrics.avg_ttft_ms:.1f}ms, itl={metrics.avg_itl_ms:.1f}ms"
        )

        # 2. Update load predictor
        self.load_predictor.add_data_point(
            num_requests=metrics.num_requests,
            avg_isl=metrics.avg_isl,
            avg_osl=metrics.avg_osl,
        )

        # 3. Update correction factors
        if self.config.enable_correction:
            self._update_correction_factors(metrics)

        # 4. Predict future load
        next_num_req, next_isl, next_osl = self.load_predictor.predict()

        if next_num_req is None or next_num_req <= 0:
            logger.warning("Load prediction invalid, skipping adjustment")
            return

        logger.info(
            f"Predicted load: requests={next_num_req:.1f}, isl={next_isl:.1f}, osl={next_osl:.1f}"
        )

        # 5. Compute scaling decision
        decision = self._compute_scaling_decision(next_num_req, next_isl, next_osl)

        # 6. Apply scaling decision
        if not self.config.no_operation:
            await self._apply_scaling_decision(decision)
        else:
            logger.info(
                f"[DRY-RUN] Would scale to: prefill={decision.num_prefill_instances}, "
                f"decode={decision.num_decode_instances}"
            )

    def _update_correction_factors(self, metrics):
        """
        Update correction factors based on observed vs expected performance.

        Correction factors adjust predictions to account for real-world deviations:
        - Prefill: TTFT affected by queuing, prefix cache hits
        - Decode: ITL affected by concurrency, chunked prefill
        """
        if not self.prefill_interpolator or not self.decode_interpolator:
            return

        # Prefill correction (TTFT)
        if metrics.avg_ttft_ms and metrics.avg_isl > 0:
            try:
                expected_ttft = self.prefill_interpolator.interpolate_ttft(metrics.avg_isl)
                if expected_ttft > 0:
                    self.prefill_correction_factor = metrics.avg_ttft_ms / expected_ttft
            except Exception as e:
                logger.warning(f"Failed to compute prefill correction factor: {e}")

        # Decode correction (ITL)
        if metrics.avg_itl_ms and metrics.num_decode_instances > 0:
            try:
                concurrency = (
                    metrics.num_requests
                    / metrics.num_decode_instances
                    * (metrics.request_duration_sec or 1.0)
                    / self.config.adjustment_interval_sec
                )
                context_length = metrics.avg_isl + metrics.avg_osl / 2

                expected_itl = self.decode_interpolator.interpolate_itl(
                    concurrency=concurrency,
                    context_length=context_length,
                )
                if expected_itl > 0:
                    self.decode_correction_factor = metrics.avg_itl_ms / expected_itl
            except Exception as e:
                logger.warning(f"Failed to compute decode correction factor: {e}")

        logger.debug(
            f"Correction factors: prefill={self.prefill_correction_factor:.3f}, "
            f"decode={self.decode_correction_factor:.3f}"
        )

    def _compute_scaling_decision(
        self,
        next_num_req: float,
        next_isl: float,
        next_osl: float,
    ):
        """
        Compute the number of prefill and decode instances needed.

        Ported from Dynamo Planner._compute_replica_requirements().

        Args:
            next_num_req: Predicted number of requests
            next_isl: Predicted input sequence length
            next_osl: Predicted output sequence length

        Returns:
            ScalingDecision with instance counts
        """
        from .types import ScalingDecision

        # === Compute Prefill replicas ===
        # Assume prefill bias is due to request queuing
        # Correction factor has linear effect on throughput
        predicted_prefill_throughput = (
            next_num_req
            * next_isl
            / self.config.adjustment_interval_sec
            * min(1.0, self.prefill_correction_factor)
        )

        if self.prefill_interpolator:
            prefill_capacity_per_gpu = self.prefill_interpolator.interpolate_thpt_per_gpu(next_isl)
        else:
            # Default estimate: 100 tokens/s/gpu for prefill
            prefill_capacity_per_gpu = 100.0

        prefill_capacity_per_instance = (
            prefill_capacity_per_gpu * self.config.prefill_gpus_per_instance
        )

        num_prefill = math.ceil(predicted_prefill_throughput / prefill_capacity_per_instance)

        logger.debug(
            f"Prefill calculation: throughput={predicted_prefill_throughput:.1f} "
            f"/ capacity={prefill_capacity_per_instance:.1f} = {num_prefill}"
        )

        # === Compute Decode replicas ===
        # Apply correction factor to ITL SLA
        if self.decode_correction_factor > 0:
            corrected_itl = self.config.target_itl_ms / self.decode_correction_factor
        else:
            corrected_itl = self.config.target_itl_ms

        if self.decode_interpolator:
            # Find best throughput that achieves corrected ITL
            (
                decode_capacity_per_gpu,
                _,
                _,
            ) = self.decode_interpolator.find_best_throughput_per_gpu(
                itl=corrected_itl,
                context_length=next_isl + next_osl / 2,
            )
        else:
            # Default estimate: 50 tokens/s/gpu for decode
            decode_capacity_per_gpu = 50.0

        decode_capacity_per_instance = (
            decode_capacity_per_gpu * self.config.decode_gpus_per_instance
        )

        predicted_decode_throughput = next_num_req * next_osl / self.config.adjustment_interval_sec

        num_decode = math.ceil(predicted_decode_throughput / decode_capacity_per_instance)

        logger.debug(
            f"Decode calculation: throughput={predicted_decode_throughput:.1f} "
            f"/ capacity={decode_capacity_per_instance:.1f} = {num_decode}"
        )

        # === Apply constraints ===
        num_prefill, num_decode = self._apply_constraints(num_prefill, num_decode)

        logger.info(
            f"Scaling decision: prefill={num_prefill}, decode={num_decode} "
            f"(load: req={next_num_req:.1f}, isl={next_isl:.1f}, osl={next_osl:.1f})"
        )

        return ScalingDecision(
            num_prefill_instances=num_prefill,
            num_decode_instances=num_decode,
            predicted_load={
                "num_requests": next_num_req,
                "isl": next_isl,
                "osl": next_osl,
            },
            reason="SLA-based autoscaling",
        )

    def _apply_constraints(self, num_prefill: int, num_decode: int) -> tuple[int, int]:
        """
        Apply min/max and GPU budget constraints.

        Args:
            num_prefill: Desired prefill instances
            num_decode: Desired decode instances

        Returns:
            (constrained_prefill, constrained_decode)
        """
        # Apply min/max constraints
        num_prefill = max(
            self.config.min_prefill_instances,
            min(num_prefill, self.config.max_prefill_instances),
        )
        num_decode = max(
            self.config.min_decode_instances,
            min(num_decode, self.config.max_decode_instances),
        )

        # Apply GPU budget constraint
        total_gpus = (
            num_prefill * self.config.prefill_gpus_per_instance
            + num_decode * self.config.decode_gpus_per_instance
        )

        if total_gpus > self.config.max_gpu_budget:
            # Scale down proportionally
            scale_factor = self.config.max_gpu_budget / total_gpus

            num_prefill = max(
                self.config.min_prefill_instances,
                int(num_prefill * scale_factor),
            )

            # Allocate remaining GPUs to decode
            remaining_gpus = (
                self.config.max_gpu_budget - num_prefill * self.config.prefill_gpus_per_instance
            )

            num_decode = max(
                self.config.min_decode_instances,
                remaining_gpus // self.config.decode_gpus_per_instance,
            )

            logger.warning(
                f"GPU budget exceeded ({total_gpus} > {self.config.max_gpu_budget}), "
                f"scaled down to prefill={num_prefill}, decode={num_decode}"
            )

        return num_prefill, num_decode

    async def _apply_scaling_decision(self, decision):
        """
        Apply the scaling decision via executor callback.

        Args:
            decision: ScalingDecision to apply
        """
        try:
            await self.executor_callback(decision)
            logger.info(
                f"Applied scaling decision: "
                f"prefill={decision.num_prefill_instances}, "
                f"decode={decision.num_decode_instances}"
            )
        except Exception as e:
            logger.error(f"Failed to apply scaling decision: {e}", exc_info=True)

    def get_status(self) -> dict:
        """Get current autoscaler status."""
        return {
            "running": self.running,
            "config": {
                "target_ttft_ms": self.config.target_ttft_ms,
                "target_itl_ms": self.config.target_itl_ms,
                "adjustment_interval_sec": self.config.adjustment_interval_sec,
            },
            "correction_factors": {
                "prefill": self.prefill_correction_factor,
                "decode": self.decode_correction_factor,
            },
            "last_adjustment_time": self.last_adjustment_time,
        }
