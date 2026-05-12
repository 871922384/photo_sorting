from __future__ import annotations


def build_qr_content(name: str, date: str, id_num: int) -> str:
    return f"NAME:{name}|DATE:{date}|ID:{id_num:03d}"


def describe_group_for_preview(index: int, group: dict) -> dict[str, str]:
    photo_count = len(group.get("photos", []))
    status = group.get("status", "unrecognized")
    recognized = status == "ok"
    return {
        "badge": "已识别" if recognized else "待确认",
        "title": f"{index + 1:02d} · {group.get('folder_name', '未命名分组')}",
        "detail": (
            f"{photo_count} 张照片，检测到患者二维码分组"
            if recognized
            else f"{photo_count} 张照片，未检测到可用二维码"
        ),
        "tone": "success" if recognized else "warning",
    }
