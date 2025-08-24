"""
基于tkinter的GUI实现
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import List, Optional
from pathlib import Path
import threading
import subprocess
import os

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

from .base import BaseThemeGUI, SudoThemeManager
from core.models import Theme
from core.theme_manager import ThemeManager
from logging_setup import get_logger
from i18n import _, init_i18n

# 初始化国际化
init_i18n()

logger = get_logger(__name__)


class SudoPasswordDialog:
    """Sudo密码输入对话框"""
    
    def __init__(self, parent, operation_name: str):
        self.result = None
        self.operation_name = operation_name
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(_("Administrator privileges required"))
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x = parent_x + (parent_width - 400) // 2
        y = parent_y + (parent_height - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self._create_dialog_widgets()
        
        # 等待用户输入
        self.password_entry.focus_set()
        self.dialog.wait_window()
    
    def _create_dialog_widgets(self):
        """创建对话框组件"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 图标和说明
        icon_frame = ttk.Frame(main_frame)
        icon_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 使用系统图标（如果可用）
        try:
            icon_label = ttk.Label(icon_frame, text="🔒", font=("", 24))
            icon_label.pack(side=tk.LEFT, padx=(0, 15))
        except:
            pass
        
        message_frame = ttk.Frame(icon_frame)
        message_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(
            message_frame, 
            text=_("Administrator privileges required"),
            font=("", 12, "bold")
        ).pack(anchor=tk.W)
        
        ttk.Label(
            message_frame,
            text=_("Operation: {operation}").format(operation=self.operation_name),
            font=("", 10)
        ).pack(anchor=tk.W, pady=(2, 0))
        
        ttk.Label(
            message_frame,
            text=_("Please enter your password to continue."),
            font=("", 10)
        ).pack(anchor=tk.W, pady=(2, 0))
        
        # 密码输入框
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill=tk.X, pady=(10, 20))
        
        ttk.Label(password_frame, text=_("Password:"), width=8).pack(side=tk.LEFT)
        
        self.password_entry = ttk.Entry(password_frame, show="*", width=30)
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.password_entry.bind("<Return>", lambda e: self._on_ok())
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame, 
            text=_("Cancel"), 
            command=self._on_cancel
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame, 
            text=_("OK"), 
            command=self._on_ok
        ).pack(side=tk.RIGHT)
    
    def _on_ok(self):
        """确定按钮事件"""
        password = self.password_entry.get()
        if password.strip():
            # 测试密码是否正确
            try:
                test_cmd = ["sudo", "-S", "-k", "true"]
                process = subprocess.Popen(
                    test_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate(input=password + '\n', timeout=10)
                
                if process.returncode == 0:
                    self.result = password
                    self.dialog.destroy()
                else:
                    messagebox.showerror(_("Error"), _("Incorrect password, please try again."), parent=self.dialog)
                    self.password_entry.delete(0, tk.END)
                    self.password_entry.focus_set()
                    
            except subprocess.TimeoutExpired:
                messagebox.showerror(_("Error"), _("Permission verification timeout."), parent=self.dialog)
            except Exception as e:
                messagebox.showerror(_("Error"), _("Permission verification failed: {error}").format(error=e), parent=self.dialog)
        else:
            messagebox.showwarning(_("Notice"), _("Please enter password."), parent=self.dialog)
    
    def _on_cancel(self):
        """取消按钮事件"""
        self.result = None
        self.dialog.destroy()


class TkinterThemeGUI(BaseThemeGUI):
    """基于tkinter的主题管理GUI"""
    
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        
        # 创建支持拖拽的根窗口
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()
            
        self.root.title(_("GRUB Theme Manager"))
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # 创建样式
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 进度窗口
        self.progress_window = None
        
        # 创建sudo包装管理器
        self.sudo_manager = SudoThemeManager(theme_manager, self)
        
        # 设置窗口图标和基本属性
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        
        # 创建界面
        self._create_widgets()
        self._setup_bindings()
        
        # 初始化数据
        self._refresh_data()
    
    def show(self) -> None:
        """显示GUI"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def hide(self) -> None:
        """隐藏GUI"""
        self.root.withdraw()
    
    def close(self) -> None:
        """关闭GUI"""
        try:
            if self.progress_window:
                self.progress_window.destroy()
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            logger.error(_("Error closing GUI: {error}").format(error=e))
    
    def show_message(self, title: str, message: str, message_type: str = "info") -> None:
        """显示消息对话框"""
        if message_type == "error":
            messagebox.showerror(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        elif message_type == "success":
            messagebox.showinfo(title, message)
        else:
            messagebox.showinfo(title, message)
    
    def show_confirmation(self, title: str, message: str) -> bool:
        """显示确认对话框"""
        return messagebox.askyesno(title, message)
    
    def select_file(self, title: str = None, 
                   filetypes: Optional[List[tuple]] = None) -> Optional[Path]:
        """文件选择对话框"""
        if title is None:
            title = _("Select file")
        if filetypes is None:
            filetypes = [(_("All files"), "*.*")]
        
        filename = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        
        return Path(filename) if filename else None
    
    def select_directory(self, title: str = None) -> Optional[Path]:
        """目录选择对话框"""
        if title is None:
            title = _("Select directory")
        dirname = filedialog.askdirectory(title=title)
        return Path(dirname) if dirname else None
    
    def prompt_input(self, title: str, prompt: str, 
                    default_value: str = "") -> Optional[str]:
        """输入对话框"""
        return simpledialog.askstring(title, prompt, initialvalue=default_value)
    
    def update_theme_list(self, themes: List[Theme]) -> None:
        """更新主题列表显示"""
        # 清空当前列表
        for item in self.theme_tree.get_children():
            self.theme_tree.delete(item)
        
        # 添加主题
        for theme in themes:
            status_text = "当前" if theme.name == self.theme_manager.current_theme else theme.status.value
            in_playlist = "是" if theme.name in self.theme_manager.playlist else "否"
            
            self.theme_tree.insert("", "end", values=(
                theme.name,
                status_text,
                in_playlist,
                theme.description or ""
            ))
    
    def update_playlist(self, playlist: List[str]) -> None:
        """更新播放列表显示"""
        # 清空当前播放列表
        self.playlist_var.set(playlist)
        
        # 更新播放列表显示
        self.playlist_listbox.delete(0, tk.END)
        for theme_name in playlist:
            self.playlist_listbox.insert(tk.END, theme_name)
    
    def update_current_theme(self, theme_name: Optional[str]) -> None:
        """更新当前主题显示"""
        if theme_name:
            self.current_theme_var.set(f"当前主题: {theme_name}")
        else:
            self.current_theme_var.set("当前主题: 未设定")
    
    def show_progress(self, title: str, message: str) -> None:
        """显示进度对话框"""
        if self.progress_window:
            self.progress_window.destroy()
        
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title(title)
        self.progress_window.geometry("300x100")
        self.progress_window.resizable(False, False)
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        
        # 居中显示
        self.progress_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 250,
            self.root.winfo_rooty() + 250
        ))
        
        # 进度消息
        ttk.Label(self.progress_window, text=message).pack(pady=20)
        
        # 进度条
        progress = ttk.Progressbar(
            self.progress_window, 
            mode='indeterminate',
            length=250
        )
        progress.pack(pady=10)
        progress.start()
        
        self.progress_window.update()
    
    def hide_progress(self) -> None:
        """隐藏进度对话框"""
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None
    
    def prompt_sudo_password(self, operation_name: str) -> Optional[str]:
        """弹出sudo密码输入对话框"""
        dialog = SudoPasswordDialog(self.root, operation_name)
        return dialog.result
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.current_theme_var = tk.StringVar()
        self.current_theme_label = ttk.Label(
            status_frame, 
            textvariable=self.current_theme_var,
            font=("", 12, "bold")
        )
        self.current_theme_label.pack(side=tk.LEFT)
        
        # 刷新按钮
        ttk.Button(
            status_frame, 
            text="刷新", 
            command=self.on_refresh
        ).pack(side=tk.RIGHT)
        
        # 主要内容区域 - 使用PanedWindow分割
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧面板 - 主题列表
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)
        
        # 主题列表标题
        ttk.Label(left_frame, text="所有主题", font=("", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # 主题列表
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        columns = ("名称", "状态", "在播放列表", "描述")
        self.theme_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        for col in columns:
            self.theme_tree.heading(col, text=col)
            self.theme_tree.column(col, width=120, minwidth=80)
        
        # 滚动条
        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.theme_tree.yview)
        self.theme_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.theme_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 主题操作按钮
        theme_buttons_frame = ttk.Frame(left_frame)
        theme_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            theme_buttons_frame, 
            text="设定主题", 
            command=self._on_set_selected_theme
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            theme_buttons_frame, 
            text="添加到播放列表", 
            command=self._on_add_selected_to_playlist
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            theme_buttons_frame, 
            text="随机主题", 
            command=self.on_random_theme
        ).pack(side=tk.RIGHT)
        
        # 右侧面板
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        # 播放列表区域
        playlist_label_frame = ttk.Frame(right_frame)
        playlist_label_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(playlist_label_frame, text="播放列表", font=("", 11, "bold")).pack(side=tk.LEFT)
        
        # 播放列表
        playlist_frame = ttk.Frame(right_frame)
        playlist_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.playlist_var = tk.Variable()
        self.playlist_listbox = tk.Listbox(playlist_frame, listvariable=self.playlist_var)
        
        playlist_scroll = ttk.Scrollbar(playlist_frame, orient=tk.VERTICAL, command=self.playlist_listbox.yview)
        self.playlist_listbox.configure(yscrollcommand=playlist_scroll.set)
        
        self.playlist_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        playlist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 播放列表操作按钮
        playlist_buttons_frame = ttk.Frame(right_frame)
        playlist_buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            playlist_buttons_frame, 
            text="从播放列表移除", 
            command=self._on_remove_from_playlist
        ).pack(fill=tk.X)
        
        # 添加主题区域
        add_frame = ttk.LabelFrame(right_frame, text="添加主题")
        add_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            add_frame, 
            text="选择文件", 
            command=self.on_add_theme_file
        ).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(
            add_frame, 
            text="选择目录", 
            command=self.on_add_theme_directory
        ).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(
            add_frame, 
            text="从URL下载", 
            command=self.on_add_theme_url
        ).pack(fill=tk.X, padx=5, pady=2)
    
    def _setup_bindings(self):
        """设置事件绑定"""
        # 双击主题列表设定主题
        self.theme_tree.bind("<Double-1>", lambda e: self._on_set_selected_theme())
        
        # 双击播放列表设定主题
        self.playlist_listbox.bind("<Double-1>", lambda e: self._on_set_playlist_theme())
        
        # 设置拖拽支持（如果可用）
        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
    
    def _refresh_data(self):
        """刷新所有数据"""
        try:
            themes = self.theme_manager.get_all_themes()
            self.update_theme_list(themes)
            self.update_playlist(self.theme_manager.playlist)
            self.update_current_theme(self.theme_manager.current_theme)
        except Exception as e:
            logger.error(f"刷新数据失败: {e}")
            self.show_message("错误", f"刷新数据失败: {e}", "error")
    
    def _on_set_selected_theme(self):
        """设定选中的主题"""
        selection = self.theme_tree.selection()
        if not selection:
            self.show_message("提示", "请先选择一个主题", "info")
            return
        
        item = selection[0]
        theme_name = self.theme_tree.item(item, "values")[0]
        
        # 在新线程中执行，避免阻塞UI
        threading.Thread(
            target=self.on_set_theme, 
            args=(theme_name,),
            daemon=True
        ).start()
    
    def _on_add_selected_to_playlist(self):
        """将选中主题添加到播放列表"""
        selection = self.theme_tree.selection()
        if not selection:
            self.show_message("提示", "请先选择一个主题", "info")
            return
        
        item = selection[0]
        theme_name = self.theme_tree.item(item, "values")[0]
        self.on_add_to_playlist(theme_name)
    
    def _on_remove_from_playlist(self):
        """从播放列表移除选中主题"""
        selection = self.playlist_listbox.curselection()
        if not selection:
            self.show_message("提示", "请先选择要移除的主题", "info")
            return
        
        theme_name = self.playlist_listbox.get(selection[0])
        self.on_remove_from_playlist(theme_name)
    
    def _on_set_playlist_theme(self):
        """设定播放列表中选中的主题"""
        selection = self.playlist_listbox.curselection()
        if not selection:
            return
        
        theme_name = self.playlist_listbox.get(selection[0])
        
        # 在新线程中执行，避免阻塞UI
        threading.Thread(
            target=self.on_set_theme, 
            args=(theme_name,),
            daemon=True
        ).start()
    
    def _on_drop(self, event):
        """处理拖拽文件事件"""
        try:
            # 获取拖拽的文件列表
            files = self.root.tk.splitlist(event.data)
            if files:
                file_path = Path(files[0])  # 只处理第一个文件
                if file_path.exists():
                    logger.info(f"拖拽文件: {file_path}")
                    # 在新线程中处理文件安装，避免阻塞GUI
                    threading.Thread(
                        target=self._install_theme_from_file,
                        args=(file_path,),
                        daemon=True
                    ).start()
                else:
                    self.show_message("错误", f"文件不存在: {file_path}", "error")
            return event.action
        except Exception as e:
            logger.error(f"处理拖拽文件失败: {e}")
            self.show_message("错误", f"处理拖拽文件失败: {e}", "error")
    
    def run(self):
        """运行GUI主循环"""
        try:
            if HAS_DND:
                logger.info("启动GUI with 拖拽支持")
            else:
                logger.info("启动GUI without 拖拽支持")
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("GUI被用户中断")
        except Exception as e:
            logger.error(f"GUI运行时出错: {e}")
            raise