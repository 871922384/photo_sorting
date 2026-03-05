# -*- coding: utf-8 -*-
"""
口腔照片自动分类工具
单文件、离线、纯 Python 的桌面 GUI 程序
基于 customtkinter 的现代化 UI
"""

import os
import re
import shutil
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk
import qrcode
import qrcode.constants as qr_constants

# CTkImage for HighDPI support
CTkImage = ctk.CTkImage

# ============================================================================
# customtkinter 基础设置
# ============================================================================

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ============================================================================
# 二维码识别库兼容性检查
# ============================================================================

HAS_PYZBAR = False
HAS_ZXING = False

try:
    from pyzbar import pyzbar  # type: ignore
    HAS_PYZBAR = True
except ImportError:
    pass

try:
    import zxingcpp  # type: ignore
    import numpy as np  # type: ignore
    HAS_ZXING = True
except ImportError:
    pass

# Pillow 兼容性
try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS  # type: ignore
except AttributeError:
    RESAMPLING_FILTER = Image.LANCZOS  # type: ignore

# 支持的图片格式
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

# ============================================================================
# 工具函数
# ============================================================================

def parse_qr_content(text: str) -> dict | None:
    """解析二维码内容"""
    try:
        parts = dict(item.split(':') for item in text.split('|'))
        return {
            'name': parts['NAME'].strip(),
            'date': parts['DATE'].strip(),
            'id': parts['ID'].strip()
        }
    except Exception:
        return None


def detect_qr_pyzbar(filepath: str) -> str | None:
    """使用 pyzbar 识别图片中的二维码"""
    try:
        img = Image.open(filepath).convert('RGB')
        img.thumbnail((1024, 1024), RESAMPLING_FILTER)
        codes = pyzbar.decode(img)
        for code in codes:
            if code.type == 'QRCODE':
                return code.data.decode('utf-8')
    except Exception:
        pass
    return None


def detect_qr_zxing(filepath: str) -> str | None:
    """使用 zxing-cpp 识别图片中的二维码"""
    try:
        img = Image.open(filepath).convert('RGB')
        img.thumbnail((1024, 1024), RESAMPLING_FILTER)
        arr = np.array(img)
        results = zxingcpp.read_barcodes(arr)
        for r in results:
            if r.format == zxingcpp.BarcodeFormat.QRCode:
                return r.text
    except Exception:
        pass
    return None


def detect_qr(filepath: str) -> str | None:
    """自动选择可用的二维码识别库"""
    if HAS_PYZBAR:
        return detect_qr_pyzbar(filepath)
    elif HAS_ZXING:
        return detect_qr_zxing(filepath)
    else:
        return None


def natural_sort_key(filename: str) -> list:
    """自然排序 key"""
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r'(\d+)', filename)
    ]


def get_sorted_images(folder: str) -> list[str]:
    """获取文件夹内所有支持的图片文件"""
    files = []
    for f in os.listdir(folder):
        ext = os.path.splitext(f)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            files.append(os.path.join(folder, f))
    files.sort(key=lambda f: natural_sort_key(os.path.basename(f)))
    return files


def resolve_folder_name(base_path: str, folder_name: str) -> str:
    """如果文件夹已存在，自动追加后缀"""
    target = os.path.join(base_path, folder_name)
    if not os.path.exists(target):
        return folder_name
    counter = 2
    while os.path.exists(os.path.join(base_path, f"{folder_name}_{counter}")):
        counter += 1
    return f"{folder_name}_{counter}"


def generate_qr_image(name: str, date: str, id_num: int) -> Image.Image:
    """生成二维码图片"""
    content = f"NAME:{name}|DATE:{date}|ID:{id_num:03d}"
    qr = qrcode.QRCode(
        version=2,
        error_correction=qr_constants.ERROR_CORRECT_H,
        box_size=6,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img  # type: ignore


def group_photos(sorted_files: list[str], progress_callback=None) -> list[dict]:
    """分组照片"""
    groups = []
    current_group = None
    unrecognized_counter = 0
    total = len(sorted_files)

    for i, filepath in enumerate(sorted_files):
        if progress_callback:
            progress_callback(i + 1, total)

        qr_content = detect_qr(filepath)
        if qr_content is not None:
            parsed = parse_qr_content(qr_content)
            if parsed:
                if current_group:
                    groups.append(current_group)
                current_group = {
                    'name': parsed['name'],
                    'date': parsed['date'],
                    'id': parsed['id'],
                    'folder_name': f"{parsed['name']}_{parsed['date']}",
                    'photos': [],
                    'qr_photo': filepath,
                    'status': 'ok'
                }
                continue

        if current_group is None:
            unrecognized_counter += 1
            current_group = {
                'name': f'未识别_{unrecognized_counter:03d}',
                'date': '',
                'id': '',
                'folder_name': f'未识别_{unrecognized_counter:03d}',
                'photos': [],
                'qr_photo': None,
                'status': 'unrecognized'
            }

        current_group['photos'].append(filepath)

    if current_group:
        groups.append(current_group)

    return groups


def execute_grouping(groups: list[dict], output_dir: str, mode: str = 'copy',
                     progress_callback=None) -> tuple[int, int, list]:
    """执行文件分组操作"""
    success_count = 0
    fail_count = 0
    log_messages = []
    total = len(groups)

    for i, group in enumerate(groups):
        try:
            folder_name = resolve_folder_name(output_dir, group['folder_name'])
            target_dir = os.path.join(output_dir, folder_name)
            os.makedirs(target_dir, exist_ok=True)

            log_messages.append(f"[OK] 创建文件夹：{folder_name}/")

            if group['qr_photo']:
                qr_dest = os.path.join(target_dir, os.path.basename(group['qr_photo']))
                shutil.copy2(group['qr_photo'], qr_dest)
                log_messages.append(f"      二维码图片：{os.path.basename(group['qr_photo'])}")

            for photo in group['photos']:
                base_name = os.path.basename(photo)
                dest = os.path.join(target_dir, base_name)
                if os.path.exists(dest):
                    name, ext = os.path.splitext(base_name)
                    counter = 1
                    while os.path.exists(dest):
                        dest = os.path.join(target_dir, f"{name}_dup{counter}{ext}")
                        counter += 1

                if mode == 'copy':
                    shutil.copy2(photo, dest)
                    log_messages.append(f"      复制：{base_name}")
                else:
                    shutil.move(photo, dest)
                    log_messages.append(f"      移动：{base_name}")

            success_count += 1
        except Exception as e:
            fail_count += 1
            log_messages.append(f"[FAIL] {group['folder_name']}: {e}")

        if progress_callback:
            progress_callback(i + 1, total)

    return success_count, fail_count, log_messages


# ============================================================================
# 主应用类
# ============================================================================

class App:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("口腔照片自动分类工具")
        self.root.geometry("800x560")
        self.root.resizable(True, True)
        self.root.minsize(700, 500)

        # 变量
        self.current_qr_image: Image.Image | None = None
        self.qr_photoimage = None
        self.preview_groups = []
        self.saved_qr_path = None
        self.processing_log = []

        # 检查依赖
        if not HAS_PYZBAR and not HAS_ZXING:
            messagebox.showerror(
                "缺少依赖",
                "未找到二维码识别库。\n\n请在命令行执行：\npip install pyzbar\n\n然后重新启动程序。"
            )
            return

        # 创建界面
        self.create_widgets()
        self.create_status_bar()

    def create_widgets(self):
        """创建主界面"""
        # 主容器
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 标题
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="口腔照片自动分类工具",
            font=ctk.CTkFont("Microsoft YaHei", 20, "bold"),
            text_color="#1E3A8A"
        )
        title_label.pack(anchor="w", pady=(0, 15))

        # Tab 视图
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True)

        self.tab_qr = self.tabview.add("  生成二维码  ")
        self.tab_sort = self.tabview.add("  整理照片  ")

        # 初始化两个 Tab
        self.init_qr_tab()
        self.init_sort_tab()

    def create_status_bar(self):
        """创建状态栏"""
        status_frame = ctk.CTkFrame(self.root, height=40, corner_radius=0)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)

        # 状态指示器
        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            width=30,
            font=ctk.CTkFont("Segoe UI", 14),
            text_color="#22C55E"
        )
        self.status_indicator.pack(side="left", padx=10)

        # 状态文本
        self.status_var = tk.StringVar(value="就绪")
        status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont("Microsoft YaHei", 12),
            anchor="w"
        )
        status_label.pack(side="left", padx=10, fill="x", expand=True)

    def init_qr_tab(self):
        """初始化二维码生成 Tab"""
        tab = self.tab_qr

        # 使用网格布局
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # 左侧面板 - 输入区
        left_panel = ctk.CTkFrame(tab, corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        left_panel.grid_columnconfigure(1, weight=1)

        # 标题
        ctk.CTkLabel(
            left_panel,
            text="患者信息",
            font=ctk.CTkFont("Microsoft YaHei", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))

        # 姓名
        ctk.CTkLabel(
            left_panel,
            text="患者姓名：",
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).grid(row=1, column=0, sticky="w", padx=20, pady=8)

        self.name_var = tk.StringVar()
        self.name_entry = ctk.CTkEntry(
            left_panel,
            textvariable=self.name_var,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13),
            corner_radius=8
        )
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=20, pady=8)

        # 日期
        ctk.CTkLabel(
            left_panel,
            text="就诊日期：",
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).grid(row=2, column=0, sticky="w", padx=20, pady=8)

        self.date_var = tk.StringVar(value=datetime.today().strftime('%Y%m%d'))
        self.date_entry = ctk.CTkEntry(
            left_panel,
            textvariable=self.date_var,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13),
            corner_radius=8
        )
        self.date_entry.grid(row=2, column=1, sticky="ew", padx=20, pady=8)

        # 序号
        ctk.CTkLabel(
            left_panel,
            text="当日序号：",
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).grid(row=3, column=0, sticky="w", padx=20, pady=8)

        self.id_var = tk.StringVar(value='001')
        self.id_entry = ctk.CTkEntry(
            left_panel,
            textvariable=self.id_var,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13),
            corner_radius=8
        )
        self.id_entry.grid(row=3, column=1, sticky="ew", padx=20, pady=8)

        # 按钮区
        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="w", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="生成二维码",
            command=self.generate_qr,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="清空",
            command=self.clear_qr,
            fg_color="transparent",
            border_width=1,
            text_color="#2563EB",
            hover_color="#DBEAFE",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).pack(side="left")

        # 编码内容显示
        content_frame = ctk.CTkFrame(left_panel, corner_radius=8)
        content_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            content_frame,
            text="编码内容：",
            font=ctk.CTkFont("Microsoft YaHei", 12)
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.content_var = tk.StringVar(value="")
        ctk.CTkLabel(
            content_frame,
            textvariable=self.content_var,
            font=ctk.CTkFont("Consolas", 11),
            anchor="w"
        ).pack(fill="x", padx=15, pady=(0, 10))

        # 右侧面板 - 预览区
        right_panel = ctk.CTkFrame(tab, corner_radius=10)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        # 标题
        ctk.CTkLabel(
            right_panel,
            text="二维码预览",
            font=ctk.CTkFont("Microsoft YaHei", 14, "bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        # 二维码显示区
        self.qr_frame = ctk.CTkFrame(
            right_panel,
            fg_color="white",
            corner_radius=8,
            border_width=2,
            border_color="#E5E7EB",
            width=320,
            height=320
        )
        self.qr_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.qr_frame.grid_propagate(False)

        self.qr_label = ctk.CTkLabel(
            self.qr_frame,
            text="点击\n生成二维码\n显示预览",
            font=ctk.CTkFont("Microsoft YaHei", 14),
            text_color="#9CA3AF",
            width=280,
            height=280
        )
        self.qr_label.pack(pady=20)

        # 操作按钮
        action_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        action_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))

        self.save_btn = ctk.CTkButton(
            action_frame,
            text="保存为图片",
            command=self.save_qr,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        )
        self.save_btn.pack(side="left", padx=(0, 10))

        self.print_btn = ctk.CTkButton(
            action_frame,
            text="打开/打印",
            command=self.open_qr,
            fg_color="transparent",
            border_width=1,
            text_color="#2563EB",
            hover_color="#DBEAFE",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        )
        self.print_btn.pack(side="left")

        # 全屏展示按钮
        self.fullscreen_btn = ctk.CTkButton(
            right_panel,
            text="📺  全屏展示（供拍摄）",
            command=self.show_fullscreen_qr,
            fg_color="#16A34A",
            hover_color="#15803D",
            corner_radius=8,
            height=40,
            font=ctk.CTkFont("Microsoft YaHei", 14, "bold"),
            state="disabled"
        )
        self.fullscreen_btn.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))

    def init_sort_tab(self):
        """初始化照片整理 Tab"""
        tab = self.tab_sort

        # 上方面板 - 设置区
        top_frame = ctk.CTkFrame(tab, corner_radius=10)
        top_frame.pack(fill="x", padx=0, pady=(0, 10))
        top_frame.grid_columnconfigure(1, weight=1)

        # 标题
        ctk.CTkLabel(
            top_frame,
            text="文件夹设置",
            font=ctk.CTkFont("Microsoft YaHei", 14, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(15, 10))

        # 源文件夹
        ctk.CTkLabel(
            top_frame,
            text="源文件夹：",
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).grid(row=1, column=0, sticky="w", padx=20, pady=8)

        self.src_var = tk.StringVar()
        self.src_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.src_var,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13),
            corner_radius=8
        )
        self.src_entry.grid(row=1, column=1, sticky="ew", padx=(10, 10), pady=8)

        ctk.CTkButton(
            top_frame,
            text="浏览",
            command=self.browse_src,
            width=80,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).grid(row=1, column=2, padx=(0, 20), pady=8)

        # 输出文件夹
        ctk.CTkLabel(
            top_frame,
            text="输出文件夹：",
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).grid(row=2, column=0, sticky="w", padx=20, pady=8)

        self.dest_var = tk.StringVar()
        self.dest_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.dest_var,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13),
            corner_radius=8,
            state="disabled"
        )
        self.dest_entry.grid(row=2, column=1, sticky="ew", padx=(10, 10), pady=8)

        self.browse_dest_btn = ctk.CTkButton(
            top_frame,
            text="浏览",
            command=self.browse_dest,
            width=80,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont("Microsoft YaHei", 13),
            state="disabled"
        )
        self.browse_dest_btn.grid(row=2, column=2, padx=(0, 20), pady=8)

        # 复选框
        self.same_folder_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            top_frame,
            text="与源文件夹相同",
            variable=self.same_folder_var,
            command=self.toggle_same_folder,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=20, pady=(5, 15))

        # 操作模式
        mode_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        mode_frame.grid(row=4, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 15))

        ctk.CTkLabel(
            mode_frame,
            text="操作模式：",
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).pack(side="left", padx=(0, 10))

        self.mode_var = tk.StringVar(value='copy')
        ctk.CTkRadioButton(
            mode_frame,
            text="复制文件",
            variable=self.mode_var,
            value='copy',
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).pack(side="left", padx=10)

        ctk.CTkRadioButton(
            mode_frame,
            text="移动文件",
            variable=self.mode_var,
            value='move',
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).pack(side="left", padx=10)

        # 中间面板 - 预览区
        middle_frame = ctk.CTkFrame(tab, corner_radius=10)
        middle_frame.pack(fill="both", expand=True)
        middle_frame.grid_columnconfigure(0, weight=1)
        middle_frame.grid_rowconfigure(1, weight=1)

        # 预览按钮
        btn_frame = ctk.CTkFrame(middle_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        self.preview_btn = ctk.CTkButton(
            btn_frame,
            text="开始预览",
            command=self.start_preview,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        )
        self.preview_btn.pack(side="left", padx=(0, 10))

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="刷新",
            command=self.refresh_preview,
            fg_color="transparent",
            border_width=1,
            text_color="#2563EB",
            hover_color="#DBEAFE",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13),
            state="disabled"
        )
        self.refresh_btn.pack(side="left")

        # 预览列表（使用 ScrollableFrame）
        list_frame = ctk.CTkFrame(middle_frame, corner_radius=8)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.scrollable_frame = ctk.CTkScrollableFrame(
            list_frame,
            corner_radius=8,
            border_width=1,
            border_color="#E5E7EB"
        )
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")

        # 预览项列表
        self.preview_items = []

        # 下方 - 进度和执行
        bottom_frame = ctk.CTkFrame(tab, corner_radius=10)
        bottom_frame.pack(fill="x", padx=0, pady=(10, 0))

        # 进度条
        self.progress_bar = ctk.CTkProgressBar(bottom_frame, height=20, corner_radius=8)
        self.progress_bar.pack(fill="x", padx=20, pady=(15, 10))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            bottom_frame,
            text="等待开始...",
            font=ctk.CTkFont("Microsoft YaHei", 12)
        )
        self.progress_label.pack(pady=(0, 15))

        # 执行按钮
        exec_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        exec_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.exec_btn = ctk.CTkButton(
            exec_frame,
            text="确认执行",
            command=self.confirm_execute,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        )
        self.exec_btn.pack(side="left", padx=(0, 10))
        self.exec_btn.configure(state="disabled")

        ctk.CTkButton(
            exec_frame,
            text="取消",
            command=self.cancel_operation,
            fg_color="transparent",
            border_width=1,
            text_color="#6B7280",
            hover_color="#F3F4F6",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13)
        ).pack(side="left", padx=(0, 10))

        self.log_btn = ctk.CTkButton(
            exec_frame,
            text="查看日志",
            command=self.show_log,
            fg_color="transparent",
            border_width=1,
            text_color="#2563EB",
            hover_color="#DBEAFE",
            corner_radius=8,
            height=36,
            font=ctk.CTkFont("Microsoft YaHei", 13),
            state="disabled"
        )
        self.log_btn.pack(side="left")

    def toggle_same_folder(self):
        """切换是否与源文件夹相同"""
        if self.same_folder_var.get():
            self.dest_var.set("")
            self.dest_entry.configure(state="disabled")
            self.browse_dest_btn.configure(state="disabled")
            if self.src_var.get():
                self.dest_var.set(self.src_var.get())
        else:
            self.dest_entry.configure(state="normal")
            self.browse_dest_btn.configure(state="normal")

    def browse_src(self):
        """浏览源文件夹"""
        folder = filedialog.askdirectory(title="选择源文件夹")
        if folder:
            self.src_var.set(folder)
            if self.same_folder_var.get():
                self.dest_var.set(folder)
            self.status_var.set(f"已选择源文件夹：{folder}")

    def browse_dest(self):
        """浏览输出文件夹"""
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.dest_var.set(folder)
            self.status_var.set(f"已选择输出文件夹：{folder}")

    def validate_qr_input(self) -> bool:
        """验证二维码输入"""
        name = self.name_var.get().strip()
        date = self.date_var.get().strip()
        id_str = self.id_var.get().strip()

        if not name:
            messagebox.showerror("验证错误", "姓名不能为空")
            return False
        if re.search(r'[/\\:*?"<>|]', name):
            messagebox.showerror("验证错误", "姓名不能包含特殊字符")
            return False

        if not re.match(r'^\d{8}$', date):
            messagebox.showerror("验证错误", "日期格式错误，请输入 8 位数字，如 20240304")
            return False

        try:
            id_num = int(id_str)
            if id_num < 1 or id_num > 999:
                raise ValueError()
        except ValueError:
            messagebox.showerror("验证错误", "序号须为 1-999 的整数")
            return False

        return True

    def generate_qr(self):
        """生成二维码"""
        if not self.validate_qr_input():
            return

        name = self.name_var.get().strip()
        date = self.date_var.get().strip()
        # 1. 读取当前序号（用于本次生成）
        id_num = int(self.id_var.get().strip())

        # 2. 生成二维码，编码内容用当前序号
        self.current_qr_image = generate_qr_image(name, date, id_num)

        # 3. 更新预览和编码内容文本（使用 280x280）
        img_size = (280, 280)
        qr_resized = self.current_qr_image.resize(img_size, RESAMPLING_FILTER)
        self.qr_photoimage = CTkImage(light_image=qr_resized, size=img_size)
        self.qr_label.configure(image=self.qr_photoimage, text="")

        content = f"NAME:{name}|DATE:{date}|ID:{id_num:03d}"
        self.content_var.set(content)

        # 4. 序号 +1，写回输入框（为下一次做准备）
        next_id = id_num + 1
        if next_id > 999:
            next_id = 1
        self.id_var.set(f"{next_id:03d}")

        self.saved_qr_path = None
        self.fullscreen_btn.configure(state="normal")
        self.status_var.set("二维码已生成")
        self.status_indicator.configure(text_color="#22C55E")

    def clear_qr(self):
        """清空二维码"""
        self.name_var.set("")
        self.date_var.set(datetime.today().strftime('%Y%m%d'))
        self.id_var.set('001')
        self.content_var.set("")
        self.qr_label.configure(image="", text="点击\n生成二维码\n显示预览")
        self.current_qr_image = None
        self.qr_photoimage = None
        self.saved_qr_path = None
        self.fullscreen_btn.configure(state="disabled")
        self.status_var.set("已清空")
        self.status_indicator.configure(text_color="#22C55E")

    def save_qr(self):
        """保存二维码"""
        if not self.current_qr_image:
            messagebox.showwarning("警告", "请先生成二维码")
            return

        name = self.name_var.get().strip()
        date = self.date_var.get().strip()

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("所有文件", "*.*")],
            initialfile=f"QR_{name}_{date}.png",
            title="保存二维码图片"
        )
        if path:
            self.current_qr_image.save(path)
            self.saved_qr_path = path
            self.status_var.set(f"已保存：{os.path.basename(path)}")
            self.status_indicator.configure(text_color="#22C55E")
            messagebox.showinfo("成功", f"二维码已保存到：\n{path}")

    def open_qr(self):
        """打开/打印二维码"""
        if not self.saved_qr_path:
            messagebox.showwarning("警告", "请先保存二维码图片")
            return

        try:
            os.startfile(self.saved_qr_path, "print")
            self.status_var.set("正在打印...")
            self.status_indicator.configure(text_color="#3B82F6")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开/打印：\n{e}")
            self.status_indicator.configure(text_color="#EF4444")

    def show_fullscreen_qr(self):
        """全屏展示二维码"""
        if self.current_qr_image is None:
            return

        # 先从 root 获取屏幕尺寸，这是可靠的
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        fs = tk.Toplevel(self.root)
        fs.configure(bg='black')
        fs.attributes('-topmost', True)
        fs.overrideredirect(True)          # 去掉标题栏和边框
        fs.geometry(f"{screen_w}x{screen_h}+0+0")   # 手动铺满屏幕，从 (0,0) 开始
        fs.lift()
        fs.focus_force()

        qr_size = int(screen_h * 0.68)
        qr_img = self.current_qr_image.resize((qr_size, qr_size), RESAMPLING_FILTER)
        qr_photo = ImageTk.PhotoImage(qr_img)

        qr_label = tk.Label(fs, image=qr_photo, bg='black')
        qr_label.image = qr_photo
        qr_label.pack(expand=True, pady=(int(screen_h * 0.04), 8))

        info_label = tk.Label(
            fs,
            text=f"{self.name_var.get()}    {self.date_var.get()}",
            font=("Microsoft YaHei", 36, "bold"),
            fg='white', bg='black'
        )
        info_label.pack(pady=(0, 16))

        hint_label = tk.Label(
            fs,
            text="按 ESC 键或单击任意位置关闭",
            font=("Microsoft YaHei", 13),
            fg='#6B7280', bg='black'
        )
        hint_label.pack()

        fs.bind('<Escape>', lambda e: fs.destroy())
        fs.bind('<Button-1>', lambda e: fs.destroy())

    def start_preview(self):
        """开始预览"""
        src = self.src_var.get().strip()
        if not src or not os.path.isdir(src):
            messagebox.showerror("错误", "请选择有效的源文件夹")
            self.status_indicator.configure(text_color="#EF4444")
            return

        self.preview_btn.configure(state="disabled")
        self.exec_btn.configure(state="disabled")
        self.status_var.set("正在扫描，请稍候...")
        self.status_indicator.configure(text_color="#3B82F6")
        self.progress_bar.set(0)
        self.progress_label.configure(text="扫描中...")

        # 清空预览列表
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.preview_items = []

        def update_progress(current, total):
            percent = current / total
            self.progress_bar.set(percent)
            self.progress_label.configure(text=f"扫描中... {current}/{total}")
            self.root.update_idletasks()

        def worker():
            try:
                files = get_sorted_images(src)
                if not files:
                    self.root.after(0, lambda: messagebox.showwarning("警告", "文件夹中没有找到支持的图片"))
                    self.root.after(0, lambda: self.status_var.set("就绪"))
                    self.root.after(0, lambda: self.status_indicator.configure(text_color="#22C55E"))
                    self.root.after(0, lambda: self.preview_btn.configure(state="normal"))
                    return

                groups = group_photos(files, update_progress)
                self.preview_groups = groups

                self.root.after(0, lambda: self.update_preview_list(groups))
                self.root.after(0, lambda: self.preview_btn.configure(state="normal"))
                self.root.after(0, lambda: self.refresh_btn.configure(state="normal"))
                self.root.after(0, lambda: self.exec_btn.configure(state="normal"))
                self.root.after(0, lambda: self.status_var.set(f"预览完成，共 {len(groups)} 组"))
                self.root.after(0, lambda: self.status_indicator.configure(text_color="#22C55E"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
                self.root.after(0, lambda: self.status_var.set("就绪"))
                self.root.after(0, lambda: self.status_indicator.configure(text_color="#EF4444"))
                self.root.after(0, lambda: self.preview_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def refresh_preview(self):
        """刷新预览"""
        self.start_preview()

    def update_preview_list(self, groups: list[dict]):
        """更新预览列表"""
        # 清空现有项
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.preview_items = []

        for i, group in enumerate(groups):
            photo_count = len(group['photos'])
            if group['status'] == 'ok':
                text = f"[OK] 组{i+1:02d}  {group['folder_name']}  ({photo_count}张)"
                color = "#22C55E"
            else:
                text = f"[WARN] 组{i+1:02d}  {group['folder_name']}  ({photo_count}张)"
                color = "#F59E0B"

            item = ctk.CTkLabel(
                self.scrollable_frame,
                text=text,
                font=ctk.CTkFont("Consolas", 12),
                text_color=color,
                anchor="w"
            )
            item.pack(fill="x", padx=10, pady=3)
            self.preview_items.append(item)

    def confirm_execute(self):
        """确认执行"""
        if not self.preview_groups:
            return

        has_unrecognized = any(g['status'] == 'unrecognized' for g in self.preview_groups)
        if has_unrecognized:
            if not messagebox.askyesno("警告", "存在未识别二维码的分组，是否继续执行？"):
                return

        if self.mode_var.get() == 'move':
            if not messagebox.askyesno("确认", "您选择的是【移动文件】模式，执行后原始文件将被移动，是否继续？"):
                return

        dest = self.dest_var.get().strip()
        if not dest or not os.path.isdir(dest):
            messagebox.showerror("错误", "请选择有效的输出文件夹")
            return

        self.exec_btn.configure(state="disabled")
        self.preview_btn.configure(state="disabled")
        self.status_var.set("正在处理，请稍候...")
        self.status_indicator.configure(text_color="#3B82F6")
        self.progress_bar.set(0)
        self.progress_label.configure(text="处理中...")

        def update_progress(current, total):
            percent = current / total
            self.progress_bar.set(percent)
            self.progress_label.configure(text=f"处理中... {current}/{total}")
            self.root.update_idletasks()

        def worker():
            try:
                success, fail, log = execute_grouping(
                    self.preview_groups, dest, self.mode_var.get(), update_progress
                )
                self.processing_log = log

                def finish():
                    self.exec_btn.configure(state="normal")
                    self.preview_btn.configure(state="normal")
                    self.log_btn.configure(state="normal")

                    if fail > 0:
                        messagebox.showwarning("完成", f"处理完成！\n成功：{success} 组\n失败：{fail} 组")
                        self.status_var.set(f"完成：成功 {success} 组，失败 {fail} 组")
                        self.status_indicator.configure(text_color="#F59E0B")
                    else:
                        messagebox.showinfo("完成", f"处理完成！\n共处理 {success} 组")
                        self.status_var.set(f"完成：{success} 组")
                        self.status_indicator.configure(text_color="#22C55E")

                self.root.after(0, finish)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
                self.root.after(0, lambda: self.status_var.set("就绪"))
                self.root.after(0, lambda: self.status_indicator.configure(text_color="#EF4444"))
                self.root.after(0, lambda: self.exec_btn.configure(state="normal"))
                self.root.after(0, lambda: self.preview_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def cancel_operation(self):
        """取消操作"""
        self.status_var.set("已取消")
        self.progress_bar.set(0)
        self.progress_label.configure(text="已取消")
        self.exec_btn.configure(state="normal")
        self.preview_btn.configure(state="normal")
        self.status_indicator.configure(text_color="#F59E0B")

    def show_log(self):
        """显示日志"""
        if not self.processing_log:
            messagebox.showinfo("日志", "暂无处理日志")
            return

        log_window = ctk.CTkToplevel(self.root)
        log_window.title("处理日志")
        log_window.geometry("500x400")
        log_window.resizable(True, True)

        text = ctk.CTkTextbox(log_window, font=ctk.CTkFont("Consolas", 11))
        text.pack(fill="both", expand=True, padx=15, pady=15)

        for line in self.processing_log:
            text.insert("end", line + "\n")

        text.configure(state="disabled")

        ctk.CTkButton(
            log_window,
            text="关闭",
            command=log_window.destroy,
            corner_radius=8,
            height=32
        ).pack(pady=(0, 15))


# ============================================================================
# 程序入口
# ============================================================================

if __name__ == '__main__':
    root = ctk.CTk()

    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = App(root)
    root.mainloop()
