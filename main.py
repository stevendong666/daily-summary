"""每日总结 - 轻量桌面应用，Python + Tkinter"""

import calendar
import json
import os
from datetime import date
import tkinter as tk
from tkinter import ttk

# ── 配色方案 ──────────────────────────────────────────────
COLORS = {
    "bg":          "#f5f5f7",
    "sidebar":     "#ffffff",
    "editor_bg":   "#ffffff",
    "accent":      "#4f6ef7",
    "accent_hover":"#3b5de7",
    "text":        "#1d1d1f",
    "text_sub":    "#86868b",
    "border":      "#e5e5ea",
    "today_bg":    "#eef1ff",
    "today_fg":    "#4f6ef7",
    "selected_bg": "#4f6ef7",
    "selected_fg": "#ffffff",
    "has_note_bg": "#f0faf0",
    "has_note_fg": "#34c759",
    "save_bg":     "#34c759",
    "save_hover":  "#2db84d",
    "unsaved_fg":  "#ff3b30",
    "placeholder": "#c7c7cc",
    "title_bar":   "#4f6ef7",
    "title_fg":    "#ffffff",
}


class DataStore:
    """数据存取，按月存储 JSON 文件"""

    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self._cache = {}

    def _month_file(self, year, month):
        return os.path.join(self.base_dir, f"{year}_{month:02d}.json")

    def load_month(self, year, month):
        key = (year, month)
        if key in self._cache:
            return self._cache[key]
        path = self._month_file(year, month)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        self._cache[key] = data
        return data

    def save_month(self, year, month, data):
        path = self._month_file(year, month)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._cache[(year, month)] = data

    def get_summary(self, date_str):
        year, month = int(date_str[:4]), int(date_str[5:7])
        return self.load_month(year, month).get(date_str)

    def save_summary(self, date_str, text):
        year, month = int(date_str[:4]), int(date_str[5:7])
        data = self.load_month(year, month)
        if text.strip():
            data[date_str] = text
        else:
            data.pop(date_str, None)
        self.save_month(year, month, data)

    def has_summary(self, date_str):
        return self.get_summary(date_str) is not None


class CalendarFrame(tk.Frame):
    """日历面板 - Canvas 绘制，支持月份切换"""

    WEEKDAYS = ("日", "一", "二", "三", "四", "五", "六")
    CELL_W = 38
    CELL_H = 32

    def __init__(self, parent, on_date_select, store, **kwargs):
        super().__init__(parent, bg=COLORS["sidebar"], **kwargs)
        self.store = store
        self.on_date_select = on_date_select
        self.today = date.today()
        self.current_year = self.today.year
        self.current_month = self.today.month
        self.selected_date = None
        self._hover_date = None

        self._build_header()
        self._build_weekday_header()
        self._build_canvas()

    def _build_header(self):
        header = tk.Frame(self, bg=COLORS["sidebar"])
        header.pack(fill="x", padx=8, pady=(12, 8))

        self.btn_prev = tk.Label(
            header, text="‹", font=("Segoe UI", 16, "bold"),
            bg=COLORS["sidebar"], fg=COLORS["text"], cursor="hand2",
        )
        self.btn_prev.pack(side="left", padx=(4, 0))
        self.btn_prev.bind("<Button-1>", lambda e: self._prev_month())
        self.btn_prev.bind("<Enter>", lambda e: self.btn_prev.config(fg=COLORS["accent"]))
        self.btn_prev.bind("<Leave>", lambda e: self.btn_prev.config(fg=COLORS["text"]))

        self.lbl_month = tk.Label(
            header, text="", font=("Microsoft YaHei", 12, "bold"),
            bg=COLORS["sidebar"], fg=COLORS["text"],
        )
        self.lbl_month.pack(side="left", expand=True)

        self.btn_next = tk.Label(
            header, text="›", font=("Segoe UI", 16, "bold"),
            bg=COLORS["sidebar"], fg=COLORS["text"], cursor="hand2",
        )
        self.btn_next.pack(side="right", padx=(0, 4))
        self.btn_next.bind("<Button-1>", lambda e: self._next_month())
        self.btn_next.bind("<Enter>", lambda e: self.btn_next.config(fg=COLORS["accent"]))
        self.btn_next.bind("<Leave>", lambda e: self.btn_next.config(fg=COLORS["text"]))

    def _build_weekday_header(self):
        row = tk.Frame(self, bg=COLORS["sidebar"])
        row.pack(fill="x", padx=8)
        for name in self.WEEKDAYS:
            lbl = tk.Label(
                row, text=name, width=4, font=("Microsoft YaHei", 9),
                bg=COLORS["sidebar"], fg=COLORS["text_sub"],
            )
            lbl.pack(side="left", expand=True)

    def _build_canvas(self):
        self.canvas = tk.Canvas(
            self, bg=COLORS["sidebar"], highlightthickness=0,
            height=self.CELL_H * 6 + 8,
        )
        self.canvas.pack(fill="x", padx=8, pady=(4, 8))
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self._draw()

    def _date_from_pos(self, x, y):
        col = int(x // self.CELL_W)
        row_idx = int(y // self.CELL_H)
        weeks = calendar.monthcalendar(self.current_year, self.current_month)
        if row_idx >= len(weeks) or col > 6:
            return None
        day = weeks[row_idx][col]
        return f"{self.current_year}-{self.current_month:02d}-{day:02d}" if day else None

    def _on_click(self, event):
        date_str = self._date_from_pos(event.x, event.y)
        if date_str:
            self.selected_date = date_str
            self._draw()
            self.on_date_select(date_str)

    def _on_motion(self, event):
        date_str = self._date_from_pos(event.x, event.y)
        if date_str != self._hover_date:
            self._hover_date = date_str
            self._draw()

    def _on_leave(self, event):
        if self._hover_date:
            self._hover_date = None
            self._draw()

    def _draw(self):
        c = self.canvas
        c.delete("all")
        W = self.CELL_W
        H = self.CELL_H
        weeks = calendar.monthcalendar(self.current_year, self.current_month)
        self.lbl_month.config(text=f"{self.current_year}年{self.current_month}月")

        for ri, week in enumerate(weeks):
            for ci, day in enumerate(week):
                x = ci * W
                y = ri * H
                if day == 0:
                    continue
                date_str = f"{self.current_year}-{self.current_month:02d}-{day:02d}"
                is_today = (
                    self.current_year == self.today.year
                    and self.current_month == self.today.month
                    and day == self.today.day
                )
                is_sel = self.selected_date == date_str
                is_hover = self._hover_date == date_str and not is_sel
                has_note = self.store.has_summary(date_str)

                # 绘制背景
                if is_sel:
                    c.create_rectangle(
                        x + 2, y + 2, x + W - 2, y + H - 2,
                        fill=COLORS["selected_bg"], outline="", width=0,
                    )
                elif is_today:
                    c.create_rectangle(
                        x + 2, y + 2, x + W - 2, y + H - 2,
                        fill=COLORS["today_bg"], outline="", width=0,
                    )
                elif is_hover:
                    c.create_rectangle(
                        x + 2, y + 2, x + W - 2, y + H - 2,
                        fill="#f0f0f5", outline="", width=0,
                    )

                # 文字颜色
                if is_sel:
                    fg = COLORS["selected_fg"]
                elif is_today:
                    fg = COLORS["today_fg"]
                elif has_note:
                    fg = COLORS["has_note_fg"]
                else:
                    fg = COLORS["text"]

                c.create_text(
                    x + W // 2, y + H // 2,
                    text=str(day), font=("Microsoft YaHei", 10),
                    fill=fg,
                )

                # 有笔记的日期下方加小圆点
                if has_note and not is_sel:
                    dot_color = COLORS["has_note_fg"] if not is_today else COLORS["today_fg"]
                    c.create_oval(
                        x + W // 2 - 2, y + H - 6,
                        x + W // 2 + 2, y + H - 2,
                        fill=dot_color, outline="",
                    )

    def _prev_month(self):
        if self.current_month == 1:
            self.current_year -= 1
            self.current_month = 12
        else:
            self.current_month -= 1
        self._draw()

    def _next_month(self):
        if self.current_month == 12:
            self.current_year += 1
            self.current_month = 1
        else:
            self.current_month += 1
        self._draw()

    def select_today(self):
        today_str = self.today.isoformat()
        self.selected_date = today_str
        self.current_year = self.today.year
        self.current_month = self.today.month
        self._draw()

    def refresh(self):
        self._draw()


class EditorFrame(tk.Frame):
    """编辑面板"""

    def __init__(self, parent, store, **kwargs):
        super().__init__(parent, bg=COLORS["editor_bg"], **kwargs)
        self.store = store
        self.current_date = None
        self._modified = False

        self._build_date_label()
        self._build_text_area()
        self._build_toolbar()

    def _build_date_label(self):
        self.lbl_date = tk.Label(
            self, text="", font=("Microsoft YaHei", 14, "bold"),
            bg=COLORS["editor_bg"], fg=COLORS["text"], anchor="w",
        )
        self.lbl_date.pack(fill="x", padx=24, pady=(20, 4))

        self.lbl_weekday = tk.Label(
            self, text="", font=("Microsoft YaHei", 10),
            bg=COLORS["editor_bg"], fg=COLORS["text_sub"], anchor="w",
        )
        self.lbl_weekday.pack(fill="x", padx=24, pady=(0, 12))

    def _build_text_area(self):
        frame = tk.Frame(self, bg=COLORS["editor_bg"])
        frame.pack(fill="both", expand=True, padx=20, pady=0)

        self.text = tk.Text(
            frame,
            font=("Microsoft YaHei", 11),
            wrap="word",
            padx=12,
            pady=10,
            bg=COLORS["editor_bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            selectbackground=COLORS["accent"],
            selectforeground="#ffffff",
            spacing1=4,
            spacing3=4,
            borderwidth=0,
            highlightthickness=1,
            highlightcolor=COLORS["accent"],
            highlightbackground=COLORS["border"],
        )
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.bind("<<Modified>>", self._on_text_modified)

    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg=COLORS["editor_bg"])
        toolbar.pack(fill="x", padx=24, pady=(8, 16))

        self.btn_save = tk.Label(
            toolbar, text="  保存  ", font=("Microsoft YaHei", 10, "bold"),
            bg=COLORS["save_bg"], fg="#ffffff", cursor="hand2",
            padx=16, pady=5,
        )
        self.btn_save.pack(side="left")
        self.btn_save.bind("<Button-1>", lambda e: self.save())
        self.btn_save.bind("<Enter>", lambda e: self.btn_save.config(bg=COLORS["save_hover"]))
        self.btn_save.bind("<Leave>", lambda e: self.btn_save.config(bg=COLORS["save_bg"]))

        self.lbl_status = tk.Label(
            toolbar, text="", font=("Microsoft YaHei", 9),
            bg=COLORS["editor_bg"], fg=COLORS["text_sub"],
        )
        self.lbl_status.pack(side="right", padx=(0, 4))

    def _on_text_modified(self, event=None):
        if self.text.edit_modified():
            self._modified = True
            self.text.edit_modified(False)
            self.lbl_status.config(text="● 未保存", fg=COLORS["unsaved_fg"])

    def load_date(self, date_str):
        if self._modified and self.current_date:
            self.save()

        self.current_date = date_str
        self.text.delete("1.0", "end")

        content = self.store.get_summary(date_str)
        if content:
            self.text.insert("1.0", content)

        self.text.edit_modified(False)
        self._modified = False

        d = date.fromisoformat(date_str)
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        self.lbl_date.config(text=f"{d.month}月{d.day}日")
        self.lbl_weekday.config(text=f"{d.year}年  {weekdays[d.weekday()]}")
        self.lbl_status.config(text="已保存", fg=COLORS["text_sub"])

    def save(self):
        if not self.current_date:
            return
        content = self.text.get("1.0", "end-1c")
        self.store.save_summary(self.current_date, content)
        self._modified = False
        self.lbl_status.config(text="已保存", fg=COLORS["text_sub"])

    def bind_save_shortcut(self, root):
        root.bind("<Control-s>", lambda e: self.save())
        root.bind("<Control-S>", lambda e: self.save())


class DailySummaryApp:
    """主窗口"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("每日总结")
        self.root.geometry("820x520")
        self.root.minsize(640, 420)
        self.root.configure(bg=COLORS["bg"])

        self.store = DataStore()

        # ── 左面板（日历） ──
        left_outer = tk.Frame(self.root, bg=COLORS["sidebar"], width=260)
        left_outer.pack(side="left", fill="y")
        left_outer.pack_propagate(False)

        # 标题栏
        title_bar = tk.Frame(left_outer, bg=COLORS["title_bar"], height=48)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(
            title_bar, text="  每日总结", font=("Microsoft YaHei", 13, "bold"),
            bg=COLORS["title_bar"], fg=COLORS["title_fg"],
        ).pack(side="left", padx=8)

        self.calendar = CalendarFrame(left_outer, self._on_date_select, self.store)
        self.calendar.pack(fill="both", expand=True)

        # 分隔线
        sep = tk.Frame(self.root, bg=COLORS["border"], width=1)
        sep.pack(side="left", fill="y")

        # ── 右面板（编辑器） ──
        right_frame = tk.Frame(self.root, bg=COLORS["editor_bg"])
        right_frame.pack(side="left", fill="both", expand=True)

        self.editor = EditorFrame(right_frame, self.store)
        self.editor.pack(fill="both", expand=True)

        self.editor.bind_save_shortcut(self.root)

        # 默认选中今天
        self.calendar.select_today()
        self._on_date_select(date.today().isoformat())

    def _on_date_select(self, date_str):
        self.editor.load_date(date_str)
        self.calendar.refresh()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = DailySummaryApp()
    app.run()
