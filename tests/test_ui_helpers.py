from ui_helpers import build_qr_content, describe_group_for_preview


def test_build_qr_content_pads_numeric_id():
    assert build_qr_content("张三", "20260512", 7) == "NAME:张三|DATE:20260512|ID:007"


def test_describe_group_for_preview_for_recognized_group():
    group = {
        "folder_name": "张三_20260512",
        "photos": ["a.jpg", "b.jpg"],
        "status": "ok",
    }

    presentation = describe_group_for_preview(0, group)

    assert presentation["badge"] == "已识别"
    assert presentation["title"] == "01 · 张三_20260512"
    assert presentation["detail"] == "2 张照片，检测到患者二维码分组"
    assert presentation["tone"] == "success"


def test_describe_group_for_preview_for_unrecognized_group():
    group = {
        "folder_name": "未识别_001",
        "photos": ["a.jpg"],
        "status": "unrecognized",
    }

    presentation = describe_group_for_preview(1, group)

    assert presentation["badge"] == "待确认"
    assert presentation["title"] == "02 · 未识别_001"
    assert presentation["detail"] == "1 张照片，未检测到可用二维码"
    assert presentation["tone"] == "warning"
