from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the packaged Windows release layout.")
    parser.add_argument("--dist-dir", required=True, help="Path to the PyInstaller dist directory.")
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir).expanduser().resolve()
    required = [
        dist_dir / "jikeyan-photo-sorting.exe",
        dist_dir / "_internal",
        dist_dir / "_internal" / "branding" / "jikeyan_app_icon.ico",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing packaged files: {missing}")

    print(f"release layout OK -> {dist_dir}")


if __name__ == "__main__":
    main()
