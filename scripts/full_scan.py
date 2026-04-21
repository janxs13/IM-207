import subprocess
import sys
from pathlib import Path


def run_step(title: str, command: list[str]) -> None:
    print(f"\n==> {title}")
    print(" ".join(command))
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    py = sys.executable

    run_step("Ruff lint", [py, "-m", "ruff", "check", str(root)])
    run_step("Pytest", [py, "-m", "pytest"])
    run_step(
        "Python compile check",
        [py, "-m", "compileall", "app.py", "routes", "services", "models", "utils"],
    )
    run_step(
        "Flask app import smoke",
        [
            py,
            "-c",
            "from app import app; print('routes_loaded=', len(app.url_map._rules))",
        ],
    )
    print("\nFull scan passed.")


if __name__ == "__main__":
    main()
