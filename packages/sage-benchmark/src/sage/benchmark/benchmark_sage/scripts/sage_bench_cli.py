import argparse

from sage.benchmark.benchmark_sage.experiments.config import ExperimentConfig, WorkloadConfig
from sage.benchmark.benchmark_sage.experiments.exp_5_1_e2e_pipeline import E2EPipelineExperiment
from sage.benchmark.benchmark_sage.experiments.exp_5_2_control_plane import ControlPlaneExperiment
from sage.benchmark.benchmark_sage.experiments.exp_5_3_isolation import IsolationExperiment
from sage.benchmark.benchmark_sage.experiments.exp_5_4_scalability import ScalabilityExperiment
from sage.benchmark.benchmark_sage.experiments.exp_5_5_heterogeneity import HeterogeneityExperiment


def main():
    parser = argparse.ArgumentParser(description="SAGE System Benchmark CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run an experiment")
    run_parser.add_argument(
        "--exp",
        type=str,
        required=True,
        choices=["5.1", "5.2", "5.3", "5.4", "5.5"],
        help="Experiment to run (e.g., 5.1)",
    )
    run_parser.add_argument("--name", type=str, default="experiment", help="Experiment name")
    run_parser.add_argument("--rate", type=float, default=10.0, help="Request rate (req/s)")
    run_parser.add_argument("--count", type=int, default=100, help="Total requests")
    run_parser.add_argument("--llm-ratio", type=float, default=0.7, help="LLM ratio")
    run_parser.add_argument(
        "--gateway", type=str, default="http://localhost:8888", help="Gateway URL"
    )
    run_parser.add_argument("--output", type=str, default="./outputs", help="Output directory")

    args = parser.parse_args()

    if args.command == "run":
        config = ExperimentConfig(
            name=args.name,
            description=f"Run {args.exp} at {args.rate} req/s",
            experiment_section=args.exp,
            gateway_url=args.gateway,
            workload=WorkloadConfig(
                total_requests=args.count, request_rate=args.rate, llm_ratio=args.llm_ratio
            ),
        )

        if args.exp == "5.2":
            exp = ControlPlaneExperiment(config, args.output, verbose=True)
        elif args.exp == "5.4":
            exp = ScalabilityExperiment(config, args.output, verbose=True)
        elif args.exp == "5.1":
            exp = E2EPipelineExperiment(config, args.output, verbose=True)
        elif args.exp == "5.5":
            exp = HeterogeneityExperiment(config, args.output, verbose=True)
        elif args.exp == "5.3":
            exp = IsolationExperiment(config, args.output, verbose=True)

        exp.setup()
        exp.run()
        exp.teardown()


if __name__ == "__main__":
    main()
