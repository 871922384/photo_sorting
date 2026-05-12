from __future__ import annotations

import re
from pathlib import Path

from PIL import Image


MIN_DIMENSIONS = {
    "jikeyan_wizard_sidebar.bmp": (300, 300),
    "jikeyan_wizard_small.bmp": (100, 100),
    "jikeyan_app_icon.ico": (256, 256),
}


def assert_dimensions(target: Path) -> None:
    minimum = MIN_DIMENSIONS.get(target.name)
    if minimum is None:
        return

    with Image.open(target) as image:
        if image.size[0] < minimum[0] or image.size[1] < minimum[1]:
            raise SystemExit(f"{target.name} below minimum dimensions: {image.size} < {minimum}")

        print(f"{target.name}: size OK -> {image.size}")


def main() -> None:
    windows_dir = Path(__file__).resolve().parent
    iss_path = windows_dir / "installer.iss"
    iss_text = iss_path.read_text(encoding="utf-8")

    for key in ("SetupIconFile", "WizardImageFile", "WizardSmallImageFile"):
        match = re.search(rf"^{key}=(.+)$", iss_text, re.M)
        if not match:
            raise SystemExit(f"missing {key} in installer.iss")
        rel_path = match.group(1).strip()
        target = (windows_dir / rel_path).resolve()
        if not target.exists():
            raise SystemExit(f"missing installer asset for {key}: {target}")
        print(f"{key}: OK -> {target}")
        assert_dimensions(target)


if __name__ == "__main__":
    main()
