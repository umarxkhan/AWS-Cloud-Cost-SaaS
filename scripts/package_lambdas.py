"""Assemble self-contained Lambda deployment packages.

Produces backend/build/<name>/ for each Lambda so that Terraform's
`archive_file` can zip a complete package (handler modules + backend/shared/ +
required third-party runtime dependencies). This prevents missing-module
runtime failures in every deployed Lambda.

Packages:
    build/api/      -> backend/api/**  + backend/shared/**  + deps ; handler.lambda_handler
    build/collect/  -> backend/collect/** + backend/shared/** + deps ; enqueue.handler / worker.handler

Third-party deps bundled (not provided by the AWS Lambda Python runtime):
    aws-lambda-powertools, pydantic
(boto3 is provided by the runtime and is NOT re-bundled by default.)

Usage (run from repo root, ideally inside the project venv):
    python scripts/package_lambdas.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
BUILD = BACKEND / "build"

# Lambda name -> (source subdirs under backend/, set of modules whose entrypoints
# are package-root-level, handler entrypoints).
LAMBDAS = {
    "api": {
        "dirs": ["api"],
        "shared": True,
        "handlers": ["handler.lambda_handler"],
    },
    "collect": {
        "dirs": ["collect"],
        "shared": True,
        "handlers": ["enqueue.handler", "worker.handler"],
    },
}


def main() -> int:
    import pip  # noqa: F401  (ensure pip available)

    for name, cfg in LAMBDAS.items():
        dst = BUILD / name
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True, exist_ok=True)

        for sub in cfg["dirs"]:
            _copytree(BACKEND / sub, dst)
        if cfg.get("shared"):
            _copytree(BACKEND / "shared", dst / "shared")

        # Install runtime deps into the package (excluding boto3, which the
        # Lambda Python runtime provides).
        subprocess.check_call(
            [
                sys.executable, "-m", "pip", "install", "--quiet",
                "--target", str(dst),
                "aws-lambda-powertools>=3,<4",
                "pydantic>=2.8,<3",
                "PyJWT>=2.8,<3",
                "cryptography>=42",
            ]
        )
        print(f"packaged build/{name}")

    print("Done. Terraform archive_file will zip these build dirs.")
    return 0


def _copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


if __name__ == "__main__":
    raise SystemExit(main())
