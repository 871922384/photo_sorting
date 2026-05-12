from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_windows_packaging_files_exist():
    expected = [
        PROJECT_ROOT / "jikeyan_photo_sorting.spec",
        PROJECT_ROOT / "packaging" / "windows" / "installer.iss",
        PROJECT_ROOT / "packaging" / "windows" / "check_installer_assets.py",
        PROJECT_ROOT / "packaging" / "windows" / "file_version_info.txt",
        PROJECT_ROOT / ".github" / "workflows" / "windows-package.yml",
    ]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in expected if not path.exists()]
    assert not missing, f"missing release files: {missing}"


def test_installer_uses_jikeyan_branding():
    installer_text = (PROJECT_ROOT / "packaging" / "windows" / "installer.iss").read_text(encoding="utf-8")

    assert '#define MyAppName "极口腔照片整理助手"' in installer_text
    assert '#define MyAppPublisher "极口腔"' in installer_text
    assert "SetupIconFile=assets/jikeyan_app_icon.ico" in installer_text
    assert "WizardImageFile=assets/jikeyan_wizard_sidebar.bmp" in installer_text
    assert "WizardSmallImageFile=assets/jikeyan_wizard_small.bmp" in installer_text


def test_pyinstaller_spec_embeds_branding_assets():
    spec_text = (PROJECT_ROOT / "jikeyan_photo_sorting.spec").read_text(encoding="utf-8")

    assert "jikeyan_app_icon.ico" in spec_text
    assert "branding" in spec_text
    assert "version_info.txt" in spec_text
    assert 'name="jikeyan-photo-sorting"' in spec_text or "name='jikeyan-photo-sorting'" in spec_text


def test_installer_assets_meet_minimum_size():
    minimum_sizes = {
        "jikeyan_app_icon.ico": (256, 256),
        "jikeyan_wizard_sidebar.bmp": (300, 300),
        "jikeyan_wizard_small.bmp": (100, 100),
    }
    asset_dir = PROJECT_ROOT / "packaging" / "windows" / "assets"

    for name, minimum_size in minimum_sizes.items():
        path = asset_dir / name
        assert path.exists(), f"missing asset: {name}"
        with Image.open(path) as image:
            assert image.size[0] >= minimum_size[0]
            assert image.size[1] >= minimum_size[1]
