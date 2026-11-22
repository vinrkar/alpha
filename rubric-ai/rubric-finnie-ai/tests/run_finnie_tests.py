# tests/run_finnie_tests.py

import argparse
import os
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = PROJECT_ROOT / "tests"

def _prepare_env() -> dict[str, str]:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    env = os.environ.copy()

    # Support projects that store the key under API_KEY in .env
    if not env.get("OPENAI_API_KEY") and env.get("API_KEY"):
        env["OPENAI_API_KEY"] = env["API_KEY"]

    return env

def build_pytest_command(
        skip_evals: bool = False,
        only_evals: bool = False,
        verbose: bool = True,
        extra_args: list[str] | None = None,
) -> list[str]:
    cmd = [sys.executable, "-m", "pytest", str(TESTS_DIR)]
    if verbose:
        cmd.append("-v")

    if skip_evals:
        cmd.extend(["-k", "not geval and not market_intelligence and not assistant_chat"])
    elif only_evals:
        cmd.extend(["-k", "geval or market_intelligence or assistant_chat"])

    if extra_args:
        cmd.extend(extra_args)

    return cmd

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Rubric Finnie AI pytest suite in a single command."
    )
    parser.add_argument(
        "--skip-evals",
        action="store_true",
        help="Skip DeepEval LLM-judge tests for fast offline/local runs.",
    )
    parser.add_argument(
        "--only-evals",
        action="store_true",
        help="Run only DeepEval GEval evaluation tests.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Run pytest with compact output instead of -v.",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional arguments forwarded directly to pytest (e.g., --maxfail=1).",
    )
    args = parser.parse_args()

    if args.skip_evals and args.only_evals:
        print("Cannot combine --skip-evals and --only-evals.", file=sys.stderr)
        return 2

    cmd = build_pytest_command(
        skip_evals=args.skip_evals,
        only_evals=args.only_evals,
        verbose=not args.quiet,
        extra_args=args.pytest_args,
    )

    print(f"Running command: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=PROJECT_ROOT, env=_prepare_env())
    return completed.returncode

if __name__ == "__main__":
    sys.exit(main())