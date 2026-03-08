# -*- coding: utf-8 -*-
"""
口腔照片自动分类工具
单文件、离线、纯 Python 的桌面 GUI 程序
基于 customtkinter 的现代化 UI
"""

import ctypes
import json
import logging
import os
import re
import shutil
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

# 在任何窗口创建之前声明 DPI Aware，防止 Windows 自动缩放导致全屏异常
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import customtkinter as ctk
from PIL import Image, ImageTk
import qrcode
import qrcode.constants as qr_constants

# CTkImage for HighDPI support
CTkImage = ctk.CTkImage

# ============================================================================
# 日志配置
# ============================================================================

def setup_logging():
    log_dir = Path.home() / '.photo_sorting'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'photo_sorting.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# customtkinter 基础设置
# ============================================================================

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ============================================================================
# Design Tokens - 视觉规范常量
# ============================================================================

class DesignTokens:
    COLOR_PAGE_BG = "#F3F4F6"
    COLOR_CARD_BG = "#FFFFFF"
    COLOR_CARD_BORDER = "#E5E7EB"
    COLOR_PRIMARY = "#2A7BF4"
    COLOR_PRIMARY_HOVER = "#1E63D8"
    COLOR_SECONDARY_BG = "#F9FAFB"
    COLOR_SECONDARY_BORDER = "#D1D5DB"
    COLOR_SECONDARY_HOVER = "#E5E7EB"
    COLOR_TEXT_PRIMARY = "#1F2937"
    COLOR_TEXT_SECONDARY = "#6B7280"
    COLOR_WHITE = "#FFFFFF"
    COLOR_SUCCESS = "#22C55E"
    COLOR_WARNING = "#F59E0B"
    COLOR_ERROR = "#EF4444"
    
    FONT_FAMILY = "Microsoft YaHei UI"
    FONT_FAMILY_FALLBACK = "Segoe UI"
    
    FONT_SIZE_TITLE = 16
    FONT_SIZE_LABEL = 14
    FONT_SIZE_INPUT = 14
    FONT_SIZE_BUTTON = 14
    FONT_SIZE_HINT = 12
    
    SPACING_PAGE = 24
    SPACING_CARD = 24
    SPACING_CARD_PADDING = 20
    SPACING_FORM_ROW = 12
    SPACING_BUTTON = 8
    SPACING_COMPONENT = 16
    
    RADIUS_CARD = 16
    RADIUS_INPUT = 12
    RADIUS_BUTTON = 12
    RADIUS_PREVIEW = 16
    
    HEIGHT_INPUT = 40
    HEIGHT_BUTTON = 42
    HEIGHT_TAB = 48
    
    QR_PREVIEW_SIZE = 260
    
    @classmethod
    def font_title(cls):
        return ctk.CTkFont(cls.FONT_FAMILY, cls.FONT_SIZE_TITLE, "bold")
    
    @classmethod
    def font_label(cls):
        return ctk.CTkFont(cls.FONT_FAMILY, cls.FONT_SIZE_LABEL)
    
    @classmethod
    def font_input(cls):
        return ctk.CTkFont(cls.FONT_FAMILY, cls.FONT_SIZE_INPUT)
    
    @classmethod
    def font_button(cls):
        return ctk.CTkFont(cls.FONT_FAMILY, cls.FONT_SIZE_BUTTON, "bold")
    
    @classmethod
    def font_hint(cls):
        return ctk.CTkFont(cls.FONT_FAMILY, cls.FONT_SIZE_HINT)

# ============================================================================
# 配置管理
# ============================================================================

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.config_dir = Path.home() / '.photo_sorting'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(exist_ok=True)
        
        self._defaults = {
            'src_folder': '',
            'dest_folder': '',
            'same_folder': True,
            'mode': 'copy',
            'last_qr_name': '',
            'last_qr_id': 1,
            'window_geometry': '800x560'
        }
        self._config = self._load()
    
    def _load(self) -> dict:
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    merged = self._defaults.copy()
                    merged.update(loaded)
                    return merged
        except Exception as e:
            logger.warning(f"加载配置失败: {e}")
        return self._defaults.copy()
    
    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            logger.debug("配置已保存")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def get(self, key: str, default=None):
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        self._config[key] = value
        self.save()
    
    @property
    def src_folder(self) -> str:
        return self._config.get('src_folder', '')
    
    @src_folder.setter
    def src_folder(self, value: str):
        self.set('src_folder', value)
    
    @property
    def dest_folder(self) -> str:
        return self._config.get('dest_folder', '')
    
    @dest_folder.setter
    def dest_folder(self, value: str):
        self.set('dest_folder', value)
    
    @property
    def same_folder(self) -> bool:
        return self._config.get('same_folder', True)
    
    @same_folder.setter
    def same_folder(self, value: bool):
        self.set('same_folder', value)
    
    @property
    def mode(self) -> str:
        return self._config.get('mode', 'copy')
    
    @mode.setter
    def mode(self, value: str):
        self.set('mode', value)
    
    @property
    def last_qr_name(self) -> str:
        return self._config.get('last_qr_name', '')
    
    @last_qr_name.setter
    def last_qr_name(self, value: str):
        self.set('last_qr_name', value)
    
    @property
    def last_qr_id(self) -> int:
        return self._config.get('last_qr_id', 1)
    
    @last_qr_id.setter
    def last_qr_id(self, value: int):
        self.set('last_qr_id', value)

config = Config()

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
    except (ValueError, KeyError) as e:
        logger.debug(f"二维码内容解析失败: {text}, 错误: {e}")
        return None


def detect_qr_pyzbar(filepath: str) -> str | None:
    """使用 pyzbar 识别图片中的二维码"""
    try:
        img = Image.open(filepath).convert('RGB')
        img.thumbnail((1024, 1024), RESAMPLING_FILTER)
        codes = pyzbar.decode(img)
        for code in codes:
            if code.type == 'QRCODE':
                result = code.data.decode('utf-8')
                logger.debug(f"pyzbar 识别成功: {filepath}")
                return result
    except (OSError, IOError) as e:
        logger.warning(f"无法打开图片文件: {filepath}, 错误: {e}")
    except Exception as e:
        logger.debug(f"pyzbar 识别失败: {filepath}, 错误: {e}")
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
                logger.debug(f"zxing-cpp 识别成功: {filepath}")
                return r.text
    except (OSError, IOError) as e:
        logger.warning(f"无法打开图片文件: {filepath}, 错误: {e}")
    except Exception as e:
        logger.debug(f"zxing-cpp 识别失败: {filepath}, 错误: {e}")
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
    
    logger.info(f"开始分组照片，共 {total} 张图片")

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
                logger.debug(f"发现二维码: {parsed['name']} ({parsed['date']})")
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
            logger.debug(f"创建未识别组: {current_group['folder_name']}")

        current_group['photos'].append(filepath)

    if current_group:
        groups.append(current_group)
    
    logger.info(f"分组完成，共 {len(groups)} 组")
    return groups


def execute_grouping(groups: list[dict], output_dir: str, mode: str = 'copy',
                     progress_callback=None) -> tuple[int, int, list]:
    """执行文件分组操作"""
    success_count = 0
    fail_count = 0
    log_messages = []
    total = len(groups)

    logger.info(f"开始执行分组操作，共 {total} 组，模式: {mode}")
    
    for i, group in enumerate(groups):
        try:
            folder_name = resolve_folder_name(output_dir, group['folder_name'])
            target_dir = os.path.join(output_dir, folder_name)
            os.makedirs(target_dir, exist_ok=True)

            log_messages.append(f"[OK] 创建文件夹：{folder_name}/")
            logger.info(f"创建文件夹: {target_dir}")

            if group['qr_photo']:
                qr_dest = os.path.join(target_dir, os.path.basename(group['qr_photo']))
                shutil.copy2(group['qr_photo'], qr_dest)
                log_messages.append(f"      二维码图片：{os.path.basename(group['qr_photo'])}")
                logger.debug(f"复制二维码图片: {group['qr_photo']} -> {qr_dest}")

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
            logger.info(f"组 {i+1}/{total} 处理完成: {folder_name}")
        except PermissionError as e:
            fail_count += 1
            log_messages.append(f"[FAIL] {group['folder_name']}: 权限错误 - {e}")
            logger.error(f"权限错误: {group['folder_name']}, {e}")
        except OSError as e:
            fail_count += 1
            log_messages.append(f"[FAIL] {group['folder_name']}: 系统错误 - {e}")
            logger.error(f"系统错误: {group['folder_name']}, {e}")
        except Exception as e:
            fail_count += 1
            log_messages.append(f"[FAIL] {group['folder_name']}: {e}")
            logger.error(f"处理失败: {group['folder_name']}, {e}")

        if progress_callback:
            progress_callback(i + 1, total)

    logger.info(f"分组操作完成，成功: {success_count}, 失败: {fail_count}")
    return success_count, fail_count, log_messages


# ============================================================================
# 主应用类
# ============================================================================

class App:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("口腔照片自动分类工具")
        self.root.geometry(config.get('window_geometry', '800x560'))
        self.root.resizable(True, True)
        self.root.minsize(700, 500)
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self.current_qr_image: Image.Image | None = None
        self.qr_photoimage = None
        self.preview_groups = []
        self.saved_qr_path = None
        self.processing_log = []

        if not HAS_PYZBAR and not HAS_ZXING:
            logger.error("缺少二维码识别库依赖")
            messagebox.showerror(
                "缺少依赖",
                "未找到二维码识别库。\n\n请在命令行执行：\npip install pyzbar\n\n然后重新启动程序。"
            )
            return

        self.create_widgets()
        self.create_status_bar()
        self._load_config()
        
        logger.info("程序启动成功")
    
    def _on_closing(self):
        self._save_config()
        logger.info("程序关闭")
        self.root.destroy()
    
    def _load_config(self):
        if config.src_folder:
            self.src_var.set(config.src_folder)
        if config.dest_folder:
            self.dest_var.set(config.dest_folder)
        self.same_folder_var.set(config.same_folder)
        self.mode_var.set(config.mode)
        if config.last_qr_name:
            self.name_var.set(config.last_qr_name)
        self.id_var.set(f"{config.last_qr_id:03d}")
        
        if not config.same_folder:
            self.dest_entry.configure(state="normal")
            self.browse_dest_btn.configure(state="normal")
        
        logger.debug("配置已加载")
    
    def _save_config(self):
        config.src_folder = self.src_var.get()
        config.dest_folder = self.dest_var.get()
        config.same_folder = self.same_folder_var.get()
        config.mode = self.mode_var.get()
        config.last_qr_name = self.name_var.get().strip()
        
        try:
            current_id = int(self.id_var.get().strip())
            config.last_qr_id = current_id
        except ValueError:
            pass
        
        geometry = self.root.geometry()
        if geometry:
            config.set('window_geometry', geometry)
        
        logger.debug("配置已保存")

    def create_widgets(self):
        """创建主界面"""
        self.root.configure(fg_color=DesignTokens.COLOR_PAGE_BG)
        
        self.main_frame = ctk.CTkFrame(
            self.root, 
            corner_radius=0, 
            fg_color=DesignTokens.COLOR_PAGE_BG
        )
        self.main_frame.pack(fill="both", expand=True, padx=DesignTokens.SPACING_PAGE, pady=DesignTokens.SPACING_PAGE)

        self.create_about_button()

        self.tabview = ctk.CTkTabview(
            self.main_frame,
            fg_color=DesignTokens.COLOR_PAGE_BG,
            segmented_button_fg_color=DesignTokens.COLOR_PAGE_BG,
            segmented_button_selected_color=DesignTokens.COLOR_PRIMARY,
            segmented_button_selected_hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            segmented_button_unselected_color=DesignTokens.COLOR_PAGE_BG,
            segmented_button_unselected_hover_color=DesignTokens.COLOR_SECONDARY_HOVER
        )
        self.tabview.pack(fill="both", expand=True)

        self.tab_qr = self.tabview.add("  生成二维码  ")
        self.tab_sort = self.tabview.add("  整理照片  ")
        
        self.tab_qr.configure(fg_color=DesignTokens.COLOR_PAGE_BG)
        self.tab_sort.configure(fg_color=DesignTokens.COLOR_PAGE_BG)

        self.init_qr_tab()
        self.init_sort_tab()

    def create_status_bar(self):
        """创建状态栏"""
        status_frame = ctk.CTkFrame(
            self.root, 
            height=40, 
            corner_radius=0,
            fg_color=DesignTokens.COLOR_WHITE,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER
        )
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)

        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            width=30,
            font=ctk.CTkFont("Segoe UI", 14),
            text_color=DesignTokens.COLOR_SUCCESS
        )
        self.status_indicator.pack(side="left", padx=DesignTokens.SPACING_BUTTON)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            anchor="w"
        )
        status_label.pack(side="left", padx=DesignTokens.SPACING_BUTTON, fill="x", expand=True)

    def create_about_button(self):
        """创建右上角关于按钮"""
        self.about_btn = ctk.CTkButton(
            self.root,
            text="ℹ️",
            width=32,
            height=32,
            corner_radius=16,
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(DesignTokens.FONT_FAMILY, 14),
            command=self.open_about
        )
        self.about_btn.place(relx=0.97, rely=0.03, anchor="ne")

    def open_about(self):
        """打开关于弹窗"""
        win = ctk.CTkToplevel(self.root)
        win.title("关于本工具")
        win.geometry("360x320")
        win.resizable(False, False)
        win.configure(fg_color=DesignTokens.COLOR_CARD_BG)
        win.transient(self.root)
        win.grab_set()

        frame = ctk.CTkFrame(
            win,
            fg_color=DesignTokens.COLOR_CARD_BG,
            corner_radius=DesignTokens.RADIUS_CARD,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER
        )
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame,
            text="关于本工具",
            font=DesignTokens.font_title(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 12))

        info = (
            "开发者：Rex Xu\n"
            "邮箱：871922384@qq.com\n"
            "版本：v1.0.0\n"
            "更新日期：2026-03-07\n\n"
            "本工具用于口腔照片的自动分类与整理，\n"
            "支持二维码生成、病人信息管理与照片分组，\n"
            "适用于内网环境下的口腔科工作流程优化。"
        )

        ctk.CTkLabel(
            frame,
            text=info,
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            justify="left"
        ).pack(anchor="w")

        ctk.CTkButton(
            frame,
            text="关闭",
            command=win.destroy,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=36,
            fg_color=DesignTokens.COLOR_PRIMARY,
            hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            text_color=DesignTokens.COLOR_WHITE,
            font=DesignTokens.font_button()
        ).pack(pady=16, anchor="e")

    def init_qr_tab(self):
        """初始化二维码生成 Tab"""
        tab = self.tab_qr

        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(
            tab, 
            corner_radius=DesignTokens.RADIUS_CARD,
            fg_color=DesignTokens.COLOR_CARD_BG,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER
        )
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, DesignTokens.SPACING_BUTTON), pady=0)
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left_panel,
            text="患者信息",
            font=DesignTokens.font_title(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(DesignTokens.SPACING_CARD_PADDING, DesignTokens.SPACING_FORM_ROW))

        name_label = ctk.CTkLabel(
            left_panel,
            text="患者姓名",
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        )
        name_label.grid(row=1, column=0, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_BUTTON))

        self.name_var = tk.StringVar()
        self.name_entry = ctk.CTkEntry(
            left_panel,
            textvariable=self.name_var,
            height=DesignTokens.HEIGHT_INPUT,
            font=DesignTokens.font_input(),
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_WHITE,
            border_color=DesignTokens.COLOR_CARD_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        )
        self.name_entry.grid(row=2, column=0, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_FORM_ROW))

        date_label = ctk.CTkLabel(
            left_panel,
            text="就诊日期",
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        )
        date_label.grid(row=3, column=0, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_BUTTON))

        self.date_var = tk.StringVar(value=datetime.today().strftime('%Y%m%d'))
        self.date_entry = ctk.CTkEntry(
            left_panel,
            textvariable=self.date_var,
            height=DesignTokens.HEIGHT_INPUT,
            font=DesignTokens.font_input(),
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_WHITE,
            border_color=DesignTokens.COLOR_CARD_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        )
        self.date_entry.grid(row=4, column=0, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_FORM_ROW))

        id_label = ctk.CTkLabel(
            left_panel,
            text="当日序号",
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        )
        id_label.grid(row=5, column=0, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_BUTTON))

        self.id_var = tk.StringVar(value='001')
        self.id_entry = ctk.CTkEntry(
            left_panel,
            textvariable=self.id_var,
            height=DesignTokens.HEIGHT_INPUT,
            font=DesignTokens.font_input(),
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_WHITE,
            border_color=DesignTokens.COLOR_CARD_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        )
        self.id_entry.grid(row=6, column=0, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_FORM_ROW))

        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.grid(row=7, column=0, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(DesignTokens.SPACING_BUTTON, DesignTokens.SPACING_CARD_PADDING))

        ctk.CTkButton(
            btn_frame,
            text="生成二维码",
            command=self.generate_qr,
            fg_color=DesignTokens.COLOR_PRIMARY,
            hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button(),
            text_color=DesignTokens.COLOR_WHITE
        ).pack(side="left", padx=(0, DesignTokens.SPACING_BUTTON))

        ctk.CTkButton(
            btn_frame,
            text="清空",
            command=self.clear_qr,
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
            border_width=1,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button()
        ).pack(side="left")

        content_frame = ctk.CTkFrame(
            left_panel, 
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_SECONDARY_BG
        )
        content_frame.grid(row=8, column=0, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_CARD_PADDING))

        ctk.CTkLabel(
            content_frame,
            text="编码内容",
            font=DesignTokens.font_hint(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        ).pack(anchor="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(DesignTokens.SPACING_BUTTON, DesignTokens.SPACING_BUTTON))

        self.content_var = tk.StringVar(value="")
        ctk.CTkLabel(
            content_frame,
            textvariable=self.content_var,
            font=ctk.CTkFont("Consolas", DesignTokens.FONT_SIZE_HINT),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_BUTTON))

        right_panel = ctk.CTkFrame(
            tab, 
            corner_radius=DesignTokens.RADIUS_CARD,
            fg_color=DesignTokens.COLOR_CARD_BG,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER
        )
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(DesignTokens.SPACING_BUTTON, 0), pady=0)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            right_panel,
            text="二维码预览",
            font=DesignTokens.font_title(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(DesignTokens.SPACING_CARD_PADDING, DesignTokens.SPACING_FORM_ROW))

        self.qr_frame = ctk.CTkFrame(
            right_panel,
            fg_color=DesignTokens.COLOR_WHITE,
            corner_radius=DesignTokens.RADIUS_PREVIEW,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER,
            width=DesignTokens.QR_PREVIEW_SIZE + 40,
            height=DesignTokens.QR_PREVIEW_SIZE + 40
        )
        self.qr_frame.grid(row=1, column=0, sticky="", padx=DesignTokens.SPACING_CARD_PADDING, pady=DesignTokens.SPACING_BUTTON)
        self.qr_frame.grid_propagate(False)

        self.qr_label = ctk.CTkLabel(
            self.qr_frame,
            text="点击「生成二维码」\n显示预览",
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY,
            width=DesignTokens.QR_PREVIEW_SIZE,
            height=DesignTokens.QR_PREVIEW_SIZE
        )
        self.qr_label.pack(expand=True)

        hint_label = ctk.CTkLabel(
            right_panel,
            text="生成后可保存为图片或全屏展示",
            font=DesignTokens.font_hint(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        )
        hint_label.grid(row=2, column=0, pady=(0, DesignTokens.SPACING_BUTTON))

        action_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_BUTTON))

        self.save_btn = ctk.CTkButton(
            action_frame,
            text="保存为图片",
            command=self.save_qr,
            fg_color=DesignTokens.COLOR_PRIMARY,
            hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button(),
            text_color=DesignTokens.COLOR_WHITE
        )
        self.save_btn.pack(side="left", padx=(0, DesignTokens.SPACING_BUTTON))

        self.print_btn = ctk.CTkButton(
            action_frame,
            text="打开/打印",
            command=self.open_qr,
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
            border_width=1,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button()
        )
        self.print_btn.pack(side="left")

        self.fullscreen_btn = ctk.CTkButton(
            right_panel,
            text="📺  全屏展示（供拍摄）",
            command=self.show_fullscreen_qr,
            fg_color=DesignTokens.COLOR_SUCCESS,
            hover_color="#15803D",
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button(),
            text_color=DesignTokens.COLOR_WHITE,
            state="disabled"
        )
        self.fullscreen_btn.grid(row=4, column=0, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_CARD_PADDING))

    def init_sort_tab(self):
        """初始化照片整理 Tab"""
        tab = self.tab_sort
        tab.configure(fg_color=DesignTokens.COLOR_PAGE_BG)

        top_frame = ctk.CTkFrame(
            tab, 
            corner_radius=DesignTokens.RADIUS_CARD,
            fg_color=DesignTokens.COLOR_CARD_BG,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER
        )
        top_frame.pack(fill="x", padx=0, pady=(0, DesignTokens.SPACING_BUTTON))
        top_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top_frame,
            text="文件夹设置",
            font=DesignTokens.font_title(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(DesignTokens.SPACING_CARD_PADDING, DesignTokens.SPACING_FORM_ROW))

        src_label = ctk.CTkLabel(
            top_frame,
            text="源文件夹",
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        )
        src_label.grid(row=1, column=0, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_BUTTON))

        self.src_var = tk.StringVar()
        self.src_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.src_var,
            height=DesignTokens.HEIGHT_INPUT,
            font=DesignTokens.font_input(),
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_WHITE,
            border_color=DesignTokens.COLOR_CARD_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        )
        self.src_entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_FORM_ROW))

        ctk.CTkButton(
            top_frame,
            text="浏览",
            command=self.browse_src,
            width=80,
            height=DesignTokens.HEIGHT_BUTTON,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            font=DesignTokens.font_button(),
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
            border_width=1,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY
        ).grid(row=2, column=2, padx=(DesignTokens.SPACING_BUTTON, DesignTokens.SPACING_CARD_PADDING), pady=(0, DesignTokens.SPACING_FORM_ROW))

        dest_label = ctk.CTkLabel(
            top_frame,
            text="输出文件夹",
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        )
        dest_label.grid(row=3, column=0, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_BUTTON))

        self.dest_var = tk.StringVar()
        self.dest_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.dest_var,
            height=DesignTokens.HEIGHT_INPUT,
            font=DesignTokens.font_input(),
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_WHITE,
            border_color=DesignTokens.COLOR_CARD_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            state="disabled"
        )
        self.dest_entry.grid(row=4, column=0, columnspan=2, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_FORM_ROW))

        self.browse_dest_btn = ctk.CTkButton(
            top_frame,
            text="浏览",
            command=self.browse_dest,
            width=80,
            height=DesignTokens.HEIGHT_BUTTON,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            font=DesignTokens.font_button(),
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
            border_width=1,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            state="disabled"
        )
        self.browse_dest_btn.grid(row=4, column=2, padx=(DesignTokens.SPACING_BUTTON, DesignTokens.SPACING_CARD_PADDING), pady=(0, DesignTokens.SPACING_FORM_ROW))

        self.same_folder_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            top_frame,
            text="与源文件夹相同",
            variable=self.same_folder_var,
            command=self.toggle_same_folder,
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            fg_color=DesignTokens.COLOR_PRIMARY,
            hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER
        ).grid(row=5, column=0, columnspan=3, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_FORM_ROW))

        mode_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        mode_frame.grid(row=6, column=0, columnspan=3, sticky="w", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_CARD_PADDING))

        ctk.CTkLabel(
            mode_frame,
            text="操作模式",
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        ).pack(side="left", padx=(0, DesignTokens.SPACING_BUTTON))

        self.mode_var = tk.StringVar(value='copy')
        ctk.CTkRadioButton(
            mode_frame,
            text="复制文件",
            variable=self.mode_var,
            value='copy',
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            fg_color=DesignTokens.COLOR_PRIMARY,
            hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER
        ).pack(side="left", padx=DesignTokens.SPACING_BUTTON)

        ctk.CTkRadioButton(
            mode_frame,
            text="移动文件",
            variable=self.mode_var,
            value='move',
            font=DesignTokens.font_label(),
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            fg_color=DesignTokens.COLOR_PRIMARY,
            hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER
        ).pack(side="left", padx=DesignTokens.SPACING_BUTTON)

        middle_frame = ctk.CTkFrame(
            tab, 
            corner_radius=DesignTokens.RADIUS_CARD,
            fg_color=DesignTokens.COLOR_CARD_BG,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER
        )
        middle_frame.pack(fill="both", expand=True)
        middle_frame.grid_columnconfigure(0, weight=1)
        middle_frame.grid_rowconfigure(1, weight=1)

        btn_frame = ctk.CTkFrame(middle_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=0, sticky="ew", padx=DesignTokens.SPACING_CARD_PADDING, pady=DesignTokens.SPACING_CARD_PADDING)

        self.preview_btn = ctk.CTkButton(
            btn_frame,
            text="开始预览",
            command=self.start_preview,
            fg_color=DesignTokens.COLOR_PRIMARY,
            hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button(),
            text_color=DesignTokens.COLOR_WHITE
        )
        self.preview_btn.pack(side="left", padx=(0, DesignTokens.SPACING_BUTTON))

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="刷新",
            command=self.refresh_preview,
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
            border_width=1,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button(),
            state="disabled"
        )
        self.refresh_btn.pack(side="left")

        list_frame = ctk.CTkFrame(
            middle_frame, 
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_WHITE,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER
        )
        list_frame.grid(row=1, column=0, sticky="nsew", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_CARD_PADDING))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.scrollable_frame = ctk.CTkScrollableFrame(
            list_frame,
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_WHITE,
            border_width=0
        )
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")

        self.preview_items = []

        bottom_frame = ctk.CTkFrame(
            tab, 
            corner_radius=DesignTokens.RADIUS_CARD,
            fg_color=DesignTokens.COLOR_CARD_BG,
            border_width=1,
            border_color=DesignTokens.COLOR_CARD_BORDER
        )
        bottom_frame.pack(fill="x", padx=0, pady=(DesignTokens.SPACING_BUTTON, 0))

        self.progress_bar = ctk.CTkProgressBar(
            bottom_frame, 
            height=12, 
            corner_radius=DesignTokens.RADIUS_INPUT,
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            progress_color=DesignTokens.COLOR_PRIMARY
        )
        self.progress_bar.pack(fill="x", padx=DesignTokens.SPACING_CARD_PADDING, pady=(DesignTokens.SPACING_CARD_PADDING, DesignTokens.SPACING_BUTTON))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            bottom_frame,
            text="等待开始...",
            font=DesignTokens.font_hint(),
            text_color=DesignTokens.COLOR_TEXT_SECONDARY
        )
        self.progress_label.pack(pady=(0, DesignTokens.SPACING_BUTTON))

        exec_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        exec_frame.pack(fill="x", padx=DesignTokens.SPACING_CARD_PADDING, pady=(0, DesignTokens.SPACING_CARD_PADDING))

        self.exec_btn = ctk.CTkButton(
            exec_frame,
            text="确认执行",
            command=self.confirm_execute,
            fg_color=DesignTokens.COLOR_PRIMARY,
            hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button(),
            text_color=DesignTokens.COLOR_WHITE
        )
        self.exec_btn.pack(side="left", padx=(0, DesignTokens.SPACING_BUTTON))
        self.exec_btn.configure(state="disabled")

        ctk.CTkButton(
            exec_frame,
            text="取消",
            command=self.cancel_operation,
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
            border_width=1,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button()
        ).pack(side="left", padx=(0, DesignTokens.SPACING_BUTTON))

        self.log_btn = ctk.CTkButton(
            exec_frame,
            text="查看日志",
            command=self.show_log,
            fg_color=DesignTokens.COLOR_SECONDARY_BG,
            hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
            border_width=1,
            border_color=DesignTokens.COLOR_SECONDARY_BORDER,
            text_color=DesignTokens.COLOR_TEXT_PRIMARY,
            corner_radius=DesignTokens.RADIUS_BUTTON,
            height=DesignTokens.HEIGHT_BUTTON,
            font=DesignTokens.font_button(),
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
        id_num = int(self.id_var.get().strip())

        self.current_qr_image = generate_qr_image(name, date, id_num)

        img_size = (DesignTokens.QR_PREVIEW_SIZE, DesignTokens.QR_PREVIEW_SIZE)
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
        self.status_indicator.configure(text_color=DesignTokens.COLOR_SUCCESS)

    def clear_qr(self):
        """清空二维码"""
        self.name_var.set("")
        self.date_var.set(datetime.today().strftime('%Y%m%d'))
        self.id_var.set('001')
        self.content_var.set("")
        self.qr_label.configure(image="", text="点击「生成二维码」\n显示预览")
        self.current_qr_image = None
        self.qr_photoimage = None
        self.saved_qr_path = None
        self.fullscreen_btn.configure(state="disabled")
        self.status_var.set("已清空")
        self.status_indicator.configure(text_color=DesignTokens.COLOR_SUCCESS)

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
            self.status_indicator.configure(text_color=DesignTokens.COLOR_SUCCESS)
            messagebox.showinfo("成功", f"二维码已保存到：\n{path}")

    def open_qr(self):
        """打开/打印二维码"""
        if not self.saved_qr_path:
            messagebox.showwarning("警告", "请先保存二维码图片")
            return

        try:
            os.startfile(self.saved_qr_path, "print")
            self.status_var.set("正在打印...")
            self.status_indicator.configure(text_color=DesignTokens.COLOR_PRIMARY)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开/打印：\n{e}")
            self.status_indicator.configure(text_color=DesignTokens.COLOR_ERROR)

    def show_fullscreen_qr(self):
        """全屏展示二维码"""
        if self.current_qr_image is None:
            return

        fs = tk.Toplevel(self.root)
        fs.configure(bg='black')
        fs.attributes('-fullscreen', True)
        fs.attributes('-topmost', True)
        fs.focus_force()

        # 等待全屏生效后获取实际窗口尺寸
        fs.update()
        screen_w = fs.winfo_width()
        screen_h = fs.winfo_height()

        qr_size = int(min(screen_w, screen_h) * 0.65)
        qr_img = self.current_qr_image.resize((qr_size, qr_size), RESAMPLING_FILTER)
        qr_photo = ImageTk.PhotoImage(qr_img)

        container = tk.Frame(fs, bg='black')
        container.place(relx=0.5, rely=0.5, anchor='center')

        qr_label = tk.Label(container, image=qr_photo, bg='black')
        qr_label.image = qr_photo
        qr_label.pack(pady=(0, 20))

        info_label = tk.Label(
            container,
            text=f"{self.name_var.get()}    {self.date_var.get()}",
            font=("Microsoft YaHei", 36, "bold"),
            fg='white', bg='black'
        )
        info_label.pack(pady=(0, 16))

        hint_label = tk.Label(
            container,
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
            self.status_indicator.configure(text_color=DesignTokens.COLOR_ERROR)
            return

        self.preview_btn.configure(state="disabled")
        self.exec_btn.configure(state="disabled")
        self.status_var.set("正在扫描，请稍候...")
        self.status_indicator.configure(text_color=DesignTokens.COLOR_PRIMARY)
        self.progress_bar.set(0)
        self.progress_label.configure(text="扫描中...")

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
                    self.root.after(0, lambda: self.status_indicator.configure(text_color=DesignTokens.COLOR_SUCCESS))
                    self.root.after(0, lambda: self.preview_btn.configure(state="normal"))
                    return

                groups = group_photos(files, update_progress)
                self.preview_groups = groups

                self.root.after(0, lambda: self.update_preview_list(groups))
                self.root.after(0, lambda: self.preview_btn.configure(state="normal"))
                self.root.after(0, lambda: self.refresh_btn.configure(state="normal"))
                self.root.after(0, lambda: self.exec_btn.configure(state="normal"))
                self.root.after(0, lambda: self.status_var.set(f"预览完成，共 {len(groups)} 组"))
                self.root.after(0, lambda: self.status_indicator.configure(text_color=DesignTokens.COLOR_SUCCESS))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
                self.root.after(0, lambda: self.status_var.set("就绪"))
                self.root.after(0, lambda: self.status_indicator.configure(text_color=DesignTokens.COLOR_ERROR))
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
        self.status_indicator.configure(text_color=DesignTokens.COLOR_PRIMARY)
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
                        self.status_indicator.configure(text_color=DesignTokens.COLOR_WARNING)
                    else:
                        messagebox.showinfo("完成", f"处理完成！\n共处理 {success} 组")
                        self.status_var.set(f"完成：{success} 组")
                        self.status_indicator.configure(text_color=DesignTokens.COLOR_SUCCESS)

                self.root.after(0, finish)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
                self.root.after(0, lambda: self.status_var.set("就绪"))
                self.root.after(0, lambda: self.status_indicator.configure(text_color=DesignTokens.COLOR_ERROR))
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
        self.status_indicator.configure(text_color=DesignTokens.COLOR_WARNING)

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

    app = App(root)
    root.mainloop()
