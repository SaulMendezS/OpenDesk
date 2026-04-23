import tkinter as tk
from tkinter import messagebox, colorchooser, filedialog
import subprocess
import os
import json
import threading
import webbrowser
import socket
import sys
import shutil
from pathlib import Path
from datetime import datetime

APP_NAME = "OpenDesk"
WINDOW_SIZE = "1240x780"


def get_resource_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_runtime_base_path():
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return os.path.join(local_appdata, "OpenDesk")
    return os.path.join(os.path.expanduser("~"), ".opendesk")


RESOURCE_BASE = get_resource_base_path()
RUNTIME_BASE = get_runtime_base_path()

DEFAULT_CONFIG_FILE = os.path.join(RESOURCE_BASE, "companies.json")
DEFAULT_STATE_FILE = os.path.join(RESOURCE_BASE, "app_state.json")

CONFIG_FILE = os.path.join(RUNTIME_BASE, "companies.json")
STATE_FILE = os.path.join(RUNTIME_BASE, "app_state.json")
LOG_DIR = os.path.join(RUNTIME_BASE, "logs")
LOG_FILE = os.path.join(LOG_DIR, "opendesk.log")
ICON_FILE = os.path.join(RESOURCE_BASE, "assets", "icons", "opendesk.ico")

COLORS = {
    "bg": "#0f172a",
    "panel": "#111827",
    "card": "#1f2937",
    "card_hover": "#2a3b52",
    "text": "#f8fafc",
    "muted": "#94a3b8",
    "primary": "#0b79d0",
    "primary_hover": "#1890f1",
    "success": "#22c55e",
    "danger": "#ef4444",
    "warning": "#f59e0b",
    "border": "#334155",
    "input": "#0b1220",
    "input_border": "#1e293b",
    "surface": "#0c1424"
}

STATUS_TEXT = {
    "unknown": "Sin verificar",
    "checking": "Verificando...",
    "online": "Disponible",
    "offline": "No disponible",
    "web": "Recurso web"
}

TYPE_ICONS = {
    "folder": "🖥",
    "web": "🌐"
}


def ensure_logs():
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


def ensure_runtime_files():
    Path(RUNTIME_BASE).mkdir(parents=True, exist_ok=True)
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    if not os.path.exists(CONFIG_FILE) and os.path.exists(DEFAULT_CONFIG_FILE):
        try:
            shutil.copy2(DEFAULT_CONFIG_FILE, CONFIG_FILE)
        except Exception:
            pass

    if not os.path.exists(STATE_FILE):
        try:
            if os.path.exists(DEFAULT_STATE_FILE):
                shutil.copy2(DEFAULT_STATE_FILE, STATE_FILE)
            else:
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def write_log(message):
    ensure_logs()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {message}\n")


def load_companies():
    if not os.path.exists(CONFIG_FILE):
        messagebox.showerror("Error", "No se encontró companies.json")
        return []

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("companies", [])
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo leer companies.json\n\n{e}")
        return []


def save_companies(companies):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"companies": companies}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar companies.json\n\n{e}")
        return False


def load_app_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_app_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_host_from_unc(path):
    if path.startswith("\\\\"):
        parts = path.strip("\\").split("\\")
        return parts[0] if parts else ""
    return ""


def can_ping(host):
    if not host:
        return False
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "500", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        return result.returncode == 0
    except Exception:
        return False


def can_resolve(host):
    if not host:
        return False
    try:
        socket.gethostbyname(host)
        return True
    except Exception:
        return False


class OpenDeskApp:
    def __init__(self, root):
        ensure_runtime_files()

        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry(WINDOW_SIZE)
        self.root.configure(bg=COLORS["bg"])
        self.root.minsize(1080, 700)

        self.set_window_icon()

        self.companies = load_companies()
        self.app_state = load_app_state()
        self.selected_company = None
        self.resource_cards = []
        self.category_sections = []
        self.search_var = tk.StringVar()
        self.logo_refs = {}
        self.results_label = None
        self.search_entry = None
        self.search_placeholder = "Buscar por nombre, ruta o IP..."
        self.is_busy = False

        self.main = tk.Frame(self.root, bg=COLORS["bg"])
        self.main.pack(fill="both", expand=True)

        self.show_company_selector()

    def set_window_icon(self):
        try:
            if os.path.exists(ICON_FILE):
                self.root.iconbitmap(ICON_FILE)
        except Exception as e:
            print("No se pudo cargar el icono:", e)

    def clear_main(self):
        for widget in self.main.winfo_children():
            widget.destroy()

    def enable_mousewheel(self, widget):
        def _on_mousewheel_windows(event):
            widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux_up(event):
            widget.yview_scroll(-1, "units")

        def _on_mousewheel_linux_down(event):
            widget.yview_scroll(1, "units")

        self.root.bind_all("<MouseWheel>", _on_mousewheel_windows)
        self.root.bind_all("<Button-4>", _on_mousewheel_linux_up)
        self.root.bind_all("<Button-5>", _on_mousewheel_linux_down)

    def disable_mousewheel(self):
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")

    def create_title(self, parent, text, size=24):
        return tk.Label(
            parent,
            text=text,
            font=("Segoe UI", size, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["text"]
        )

    def create_subtitle(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 11),
            bg=COLORS["bg"],
            fg=COLORS["muted"]
        )

    def copy_to_clipboard(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            messagebox.showinfo("Copiado", "El enlace fue copiado al portapapeles.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar el enlace.\n\nDetalle: {e}")

    def resolve_user_or_resource_path(self, relative_path):
        if not relative_path:
            return None

        runtime_path = os.path.join(RUNTIME_BASE, relative_path)
        if os.path.exists(runtime_path):
            return runtime_path

        resource_path = os.path.join(RESOURCE_BASE, relative_path)
        if os.path.exists(resource_path):
            return resource_path

        return None

    def load_logo(self, path, target_width=90):
        if not path:
            return None

        full_path = self.resolve_user_or_resource_path(path)
        if not full_path:
            return None

        try:
            img = tk.PhotoImage(file=full_path)
            width = img.width()
            if width > target_width:
                factor = max(1, width // target_width)
                img = img.subsample(factor, factor)
            return img
        except Exception:
            return None

    def add_card_hover(self, card):
        def set_bg(widget, bg):
            try:
                if isinstance(widget, (tk.Frame, tk.Label, tk.Canvas)):
                    widget.configure(bg=bg)
            except Exception:
                pass
            for child in widget.winfo_children():
                if isinstance(child, tk.Button):
                    continue
                set_bg(child, bg)

        def on_enter(_):
            set_bg(card, COLORS["card_hover"])

        def on_leave(_):
            set_bg(card, COLORS["card"])

        def bind_recursive(widget):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            for child in widget.winfo_children():
                if not isinstance(child, tk.Button):
                    bind_recursive(child)

        bind_recursive(card)

    def set_last_company(self, company_name):
        self.app_state["last_company"] = company_name
        save_app_state(self.app_state)

    def get_last_company(self):
        return self.app_state.get("last_company")

    def get_company_by_name(self, name):
        for company in self.companies:
            if company.get("name") == name:
                return company
        return None

    def set_search_placeholder(self):
        if self.search_entry:
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, self.search_placeholder)
            self.search_entry.config(fg=COLORS["muted"])

    def clear_search_placeholder(self, event=None):
        if self.search_entry and self.search_entry.get() == self.search_placeholder:
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg=COLORS["text"])

    def restore_search_placeholder(self, event=None):
        if self.search_entry and not self.search_entry.get().strip():
            self.set_search_placeholder()

    def get_search_text(self):
        value = self.search_var.get().strip()
        if value == self.search_placeholder:
            return ""
        return value.lower()

    def open_add_company_window(self):
        win = tk.Toplevel(self.root)
        win.title("Agregar empresa")
        win.geometry("980x620")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        try:
            if os.path.exists(ICON_FILE):
                win.iconbitmap(ICON_FILE)
        except Exception:
            pass

        outer = tk.Frame(win, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        left = tk.Frame(
            outer,
            bg=COLORS["card"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            width=320
        )
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)

        right = tk.Frame(
            outer,
            bg=COLORS["card"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        right.pack(side="left", fill="both", expand=True)

        name_var = tk.StringVar()
        desc_var = tk.StringVar()
        color_var = tk.StringVar(value="#0b79d0")
        logo_var = tk.StringVar()

        tk.Label(
            left,
            text="Vista previa",
            font=("Segoe UI", 17, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"]
        ).pack(anchor="w", padx=18, pady=(18, 6))

        tk.Label(
            left,
            text="Así se verá la nueva empresa en OpenDesk.",
            font=("Segoe UI", 10),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=260,
            justify="left"
        ).pack(anchor="w", padx=18, pady=(0, 16))

        preview_card = tk.Frame(
            left,
            bg=COLORS["panel"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        preview_card.pack(fill="x", padx=18, pady=(0, 16))

        preview_bar = tk.Frame(preview_card, bg=color_var.get(), height=8)
        preview_bar.pack(fill="x")

        preview_body = tk.Frame(preview_card, bg=COLORS["panel"])
        preview_body.pack(fill="both", expand=True, padx=16, pady=16)

        preview_logo_label = tk.Label(preview_body, bg=COLORS["panel"], fg=COLORS["muted"])
        preview_logo_label.pack(anchor="w", pady=(0, 12))

        preview_name = tk.Label(
            preview_body,
            text="Nueva empresa",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["text"]
        )
        preview_name.pack(anchor="w")

        preview_desc = tk.Label(
            preview_body,
            text="Descripción de la empresa",
            font=("Segoe UI", 10),
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            wraplength=250,
            justify="left"
        )
        preview_desc.pack(anchor="w", pady=(8, 16))

        preview_button = tk.Button(
            preview_body,
            text="Entrar",
            font=("Segoe UI", 10, "bold"),
            bg=color_var.get(),
            fg="white",
            bd=0,
            padx=16,
            pady=10,
            cursor="hand2"
        )
        preview_button.pack(anchor="w")

        helper_box = tk.Frame(left, bg=COLORS["surface"])
        helper_box.pack(fill="x", padx=18, pady=(0, 18))

        tk.Label(
            helper_box,
            text="Consejos",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["surface"],
            fg=COLORS["text"]
        ).pack(anchor="w", padx=12, pady=(10, 4))

        tk.Label(
            helper_box,
            text="• El color se puede elegir con la paleta.\n• El logo se copia a assets/logos.\n• La empresa se guarda en companies.json.",
            font=("Segoe UI", 9),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            justify="left",
            wraplength=260
        ).pack(anchor="w", padx=12, pady=(0, 10))

        header = tk.Frame(right, bg=COLORS["card"])
        header.pack(fill="x", padx=22, pady=(18, 10))

        tk.Label(
            header,
            text="Nueva empresa",
            font=("Segoe UI", 19, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"]
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Completa la información base para crear una nueva empresa.",
            font=("Segoe UI", 10),
            bg=COLORS["card"],
            fg=COLORS["muted"]
        ).pack(anchor="w", pady=(6, 0))

        form = tk.Frame(right, bg=COLORS["card"])
        form.pack(fill="both", expand=True, padx=22, pady=(8, 0))

        def create_label(parent, text):
            tk.Label(
                parent,
                text=text,
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"],
                fg=COLORS["text"]
            ).pack(anchor="w", pady=(10, 6))

        def create_entry(parent, variable):
            frame = tk.Frame(
                parent,
                bg=COLORS["input"],
                bd=1,
                relief="solid",
                highlightbackground=COLORS["input_border"],
                highlightthickness=1
            )
            frame.pack(fill="x")
            entry = tk.Entry(
                frame,
                textvariable=variable,
                font=("Segoe UI", 10),
                bg=COLORS["input"],
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat"
            )
            entry.pack(fill="x", padx=12, pady=10)
            return entry

        create_label(form, "Nombre")
        name_entry = create_entry(form, name_var)

        create_label(form, "Descripción")
        create_entry(form, desc_var)

        create_label(form, "Color principal")
        color_row = tk.Frame(form, bg=COLORS["card"])
        color_row.pack(fill="x")

        color_preview = tk.Frame(
            color_row,
            bg=color_var.get(),
            width=48,
            height=48,
            bd=1,
            relief="solid",
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        color_preview.pack(side="left")
        color_preview.pack_propagate(False)

        color_entry_wrap = tk.Frame(
            color_row,
            bg=COLORS["input"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["input_border"],
            highlightthickness=1
        )
        color_entry_wrap.pack(side="left", fill="x", expand=True, padx=(10, 10))

        tk.Entry(
            color_entry_wrap,
            textvariable=color_var,
            font=("Segoe UI", 10),
            bg=COLORS["input"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat"
        ).pack(fill="x", padx=12, pady=10)

        def choose_color():
            selected = colorchooser.askcolor(
                color=color_var.get(),
                title="Selecciona un color principal",
                parent=win
            )
            if selected and selected[1]:
                color_var.set(selected[1])
                refresh_preview()

        tk.Button(
            color_row,
            text="Elegir color",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["primary"],
            fg="white",
            bd=0,
            padx=14,
            pady=12,
            cursor="hand2",
            command=choose_color
        ).pack(side="left")

        create_label(form, "Logo")
        logo_row = tk.Frame(form, bg=COLORS["card"])
        logo_row.pack(fill="x")

        logo_entry_wrap = tk.Frame(
            logo_row,
            bg=COLORS["input"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["input_border"],
            highlightthickness=1
        )
        logo_entry_wrap.pack(side="left", fill="x", expand=True)

        tk.Entry(
            logo_entry_wrap,
            textvariable=logo_var,
            font=("Segoe UI", 10),
            bg=COLORS["input"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat"
        ).pack(fill="x", padx=12, pady=10)

        def choose_logo():
            file_path = filedialog.askopenfilename(
                parent=win,
                title="Selecciona un logo",
                filetypes=[
                    ("Imágenes PNG", "*.png"),
                    ("Imágenes GIF", "*.gif"),
                    ("Imágenes soportadas", "*.png;*.gif")
                ]
            )
            if file_path:
                logo_var.set(file_path)
                refresh_preview()

        tk.Button(
            logo_row,
            text="Seleccionar",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["card_hover"],
            fg=COLORS["text"],
            bd=0,
            padx=14,
            pady=12,
            cursor="hand2",
            command=choose_logo
        ).pack(side="left", padx=(10, 0))

        tk.Label(
            form,
            text="Puedes escribir la ruta del logo o seleccionarlo. Se copiará automáticamente a assets/logos.",
            font=("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=560,
            justify="left"
        ).pack(anchor="w", pady=(12, 0))

        footer = tk.Frame(right, bg=COLORS["card"])
        footer.pack(fill="x", padx=22, pady=22)

        def normalize_hex(value):
            value = value.strip()
            if not value:
                return "#0b79d0"
            if not value.startswith("#"):
                value = "#" + value
            return value

        def refresh_preview(*args):
            color = normalize_hex(color_var.get())
            preview_bar.configure(bg=color)
            preview_button.configure(bg=color)
            color_preview.configure(bg=color)

            preview_name.configure(text=name_var.get().strip() or "Nueva empresa")
            preview_desc.configure(text=desc_var.get().strip() or "Descripción de la empresa")

            logo_path = logo_var.get().strip()
            if logo_path:
                img = None

                if os.path.exists(logo_path):
                    try:
                        img = tk.PhotoImage(file=logo_path)
                    except Exception:
                        img = None
                else:
                    img = self.load_logo(logo_path, target_width=120)

                if img:
                    if img.width() > 120:
                        factor = max(1, img.width() // 120)
                        img = img.subsample(factor, factor)
                    self.logo_refs["new_company_preview"] = img
                    preview_logo_label.configure(image=img, text="")
                else:
                    preview_logo_label.configure(image="", text="Logo no disponible")
            else:
                preview_logo_label.configure(image="", text="Sin logo")

        def save_new_company():
            name = name_var.get().strip()
            desc = desc_var.get().strip()
            color = normalize_hex(color_var.get())
            logo_input = logo_var.get().strip()

            if not name:
                messagebox.showwarning("Falta información", "Debes ingresar un nombre para la empresa.", parent=win)
                return

            if self.get_company_by_name(name):
                messagebox.showwarning("Duplicado", "Ya existe una empresa con ese nombre.", parent=win)
                return

            logo_relative_path = ""

            if logo_input:
                logos_dir = os.path.join(RUNTIME_BASE, "assets", "logos")
                Path(logos_dir).mkdir(parents=True, exist_ok=True)

                if os.path.exists(logo_input):
                    _, ext = os.path.splitext(logo_input)
                    safe_name = "".join(c for c in name.lower().replace(" ", "_") if c.isalnum() or c == "_")
                    ext = ext.lower() if ext else ".png"
                    destination = os.path.join(logos_dir, f"{safe_name}{ext}")
                    try:
                        shutil.copy2(logo_input, destination)
                        logo_relative_path = f"assets/logos/{os.path.basename(destination)}"
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo copiar el logo.\n\nDetalle: {e}", parent=win)
                        return
                else:
                    logo_relative_path = logo_input

            new_company = {
                "name": name,
                "description": desc or "Sin descripción.",
                "theme_color": color,
                "logo": logo_relative_path,
                "categories": []
            }

            self.companies.append(new_company)

            if save_companies(self.companies):
                self.companies = load_companies()
                messagebox.showinfo("Éxito", "Empresa agregada correctamente.", parent=win)
                win.destroy()
                self.show_company_selector()

        tk.Button(
            footer,
            text="Cancelar",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["card_hover"],
            fg=COLORS["text"],
            bd=0,
            padx=16,
            pady=10,
            cursor="hand2",
            command=win.destroy
        ).pack(side="right")

        tk.Button(
            footer,
            text="Crear empresa",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["primary"],
            fg="white",
            bd=0,
            padx=16,
            pady=10,
            cursor="hand2",
            command=save_new_company
        ).pack(side="right", padx=(0, 10))

        name_var.trace_add("write", refresh_preview)
        desc_var.trace_add("write", refresh_preview)
        color_var.trace_add("write", refresh_preview)
        logo_var.trace_add("write", refresh_preview)

        refresh_preview()
        name_entry.focus_set()

    def show_company_selector(self):
        self.disable_mousewheel()
        self.clear_main()
        self.selected_company = None
        self.resource_cards = []
        self.category_sections = []
        self.logo_refs = {}

        wrapper = tk.Frame(self.main, bg=COLORS["bg"])
        wrapper.pack(fill="both", expand=True, padx=32, pady=28)

        self.create_title(wrapper, "OpenDesk", 28).pack(anchor="w")
        self.create_subtitle(
            wrapper,
            "Selecciona una empresa para cargar sus accesos y herramientas."
        ).pack(anchor="w", pady=(6, 14))

        top_actions = tk.Frame(wrapper, bg=COLORS["bg"])
        top_actions.pack(fill="x", pady=(0, 18))

        tk.Button(
            top_actions,
            text="+ Agregar empresa",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["primary"],
            fg="white",
            bd=0,
            padx=14,
            pady=10,
            cursor="hand2",
            command=self.open_add_company_window
        ).pack(side="right")

        last_company_name = self.get_last_company()
        last_company = self.get_company_by_name(last_company_name) if last_company_name else None

        if last_company:
            quick = tk.Frame(
                wrapper,
                bg=COLORS["card"],
                bd=1,
                relief="solid",
                highlightbackground=COLORS["border"],
                highlightthickness=1
            )
            quick.pack(fill="x", pady=(0, 20))

            inner = tk.Frame(quick, bg=COLORS["card"])
            inner.pack(fill="x", padx=16, pady=14)

            tk.Label(
                inner,
                text=f"Última empresa abierta: {last_company_name}",
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"],
                fg=COLORS["text"]
            ).pack(side="left")

            tk.Button(
                inner,
                text="Continuar",
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["primary"],
                fg="white",
                bd=0,
                padx=14,
                pady=8,
                cursor="hand2",
                command=lambda c=last_company: self.show_dashboard(c)
            ).pack(side="right")

        grid = tk.Frame(wrapper, bg=COLORS["bg"])
        grid.pack(fill="both", expand=True)

        for i in range(3):
            grid.grid_columnconfigure(i, weight=1)

        if not self.companies:
            tk.Label(
                grid,
                text="No hay empresas configuradas.",
                font=("Segoe UI", 12),
                bg=COLORS["bg"],
                fg=COLORS["danger"]
            ).pack(pady=40)
            return

        for i, company in enumerate(self.companies):
            row, col = divmod(i, 3)
            card = tk.Frame(
                grid,
                bg=COLORS["card"],
                bd=1,
                relief="solid",
                highlightbackground=COLORS["border"],
                highlightthickness=1
            )
            card.grid(row=row, column=col, sticky="nsew", padx=10, pady=10, ipadx=12, ipady=12)

            top_bar = tk.Frame(card, bg=company.get("theme_color", COLORS["primary"]), height=8)
            top_bar.pack(fill="x")

            body = tk.Frame(card, bg=COLORS["card"])
            body.pack(fill="both", expand=True, padx=18, pady=18)

            logo_path = company.get("logo", "")
            logo = self.load_logo(logo_path, target_width=120)
            if logo:
                self.logo_refs[f"selector_{company.get('name')}"] = logo
                tk.Label(body, image=logo, bg=COLORS["card"]).pack(anchor="w", pady=(0, 12))

            tk.Label(
                body,
                text=company.get("name", "Empresa"),
                font=("Segoe UI", 16, "bold"),
                bg=COLORS["card"],
                fg=COLORS["text"]
            ).pack(anchor="w")

            tk.Label(
                body,
                text=company.get("description", ""),
                font=("Segoe UI", 10),
                bg=COLORS["card"],
                fg=COLORS["muted"],
                justify="left",
                wraplength=280
            ).pack(anchor="w", pady=(8, 18))

            tk.Button(
                body,
                text="Entrar",
                font=("Segoe UI", 10, "bold"),
                bg=company.get("theme_color", COLORS["primary"]),
                fg="white",
                bd=0,
                padx=14,
                pady=10,
                cursor="hand2",
                command=lambda c=company: self.show_dashboard(c)
            ).pack(anchor="w")

            self.add_card_hover(card)

    def show_dashboard(self, company):
        self.disable_mousewheel()
        self.clear_main()
        self.selected_company = company
        self.resource_cards = []
        self.category_sections = []
        self.logo_refs = {}
        self.search_var.set("")
        self.set_last_company(company.get("name", ""))

        outer = tk.Frame(self.main, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True)

        sidebar = tk.Frame(outer, bg=COLORS["panel"], width=260)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        content = tk.Frame(outer, bg=COLORS["bg"])
        content.pack(side="left", fill="both", expand=True)

        logo_path = company.get("logo", "")
        logo = self.load_logo(logo_path, target_width=120)
        if logo:
            self.logo_refs[f"dashboard_{company.get('name')}"] = logo
            tk.Label(sidebar, image=logo, bg=COLORS["panel"]).pack(anchor="w", padx=20, pady=(22, 8))
        else:
            tk.Label(
                sidebar,
                text="OpenDesk",
                font=("Segoe UI", 22, "bold"),
                bg=COLORS["panel"],
                fg=COLORS["text"]
            ).pack(anchor="w", padx=20, pady=(24, 6))

        tk.Label(
            sidebar,
            text=company.get("name", "Empresa"),
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["text"]
        ).pack(anchor="w", padx=20)

        tk.Label(
            sidebar,
            text=company.get("description", ""),
            font=("Segoe UI", 9),
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            wraplength=210,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(8, 20))

        tk.Button(
            sidebar,
            text="← Volver",
            font=("Segoe UI", 10, "bold"),
            bg=company.get("theme_color", COLORS["primary"]),
            fg="white",
            bd=0,
            padx=12,
            pady=10,
            cursor="hand2",
            command=self.show_company_selector
        ).pack(fill="x", padx=20, pady=(0, 10))

        tk.Button(
            sidebar,
            text="Verificar recursos",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            bd=0,
            padx=12,
            pady=10,
            cursor="hand2",
            command=self.check_all_resources
        ).pack(fill="x", padx=20, pady=(0, 10))

        tk.Button(
            sidebar,
            text="Abrir todos",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            bd=0,
            padx=12,
            pady=10,
            cursor="hand2",
            command=self.open_all_resources
        ).pack(fill="x", padx=20, pady=(0, 10))

        top = tk.Frame(content, bg=COLORS["bg"])
        top.pack(fill="x", padx=26, pady=(24, 14))

        header_row = tk.Frame(top, bg=COLORS["bg"])
        header_row.pack(fill="x")

        tk.Label(
            header_row,
            text=company.get("name", "Empresa"),
            font=("Segoe UI", 26, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["text"]
        ).pack(anchor="w", side="left")

        self.results_label = tk.Label(
            header_row,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"]
        )
        self.results_label.pack(anchor="e", side="right", pady=(8, 0))

        tk.Label(
            top,
            text="Centro de accesos y monitoreo interno.",
            font=("Segoe UI", 11),
            bg=COLORS["bg"],
            fg=COLORS["muted"]
        ).pack(anchor="w", pady=(6, 14))

        metrics = tk.Frame(top, bg=COLORS["bg"])
        metrics.pack(fill="x", pady=(0, 16))

        total_resources = sum(len(cat.get("resources", [])) for cat in company.get("categories", []))
        self.create_metric(metrics, "Categorías", str(len(company.get("categories", []))), 0)
        self.create_metric(metrics, "Recursos", str(total_resources), 1)
        self.create_metric(metrics, "Empresa", company.get("name", "-"), 2)

        search_wrap = tk.Frame(top, bg=COLORS["bg"])
        search_wrap.pack(fill="x")

        tk.Label(
            search_wrap,
            text="Buscar:",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["text"]
        ).pack(side="left", padx=(0, 8))

        search_box = tk.Frame(
            search_wrap,
            bg=COLORS["input"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["input_border"],
            highlightthickness=1
        )
        search_box.pack(side="left", ipady=3)

        tk.Label(
            search_box,
            text="🔍",
            font=("Segoe UI", 10),
            bg=COLORS["input"],
            fg=COLORS["muted"]
        ).pack(side="left", padx=(8, 4))

        self.search_entry = tk.Entry(
            search_box,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
            bg=COLORS["input"],
            fg=COLORS["muted"],
            insertbackground=COLORS["text"],
            relief="flat",
            width=42
        )
        self.search_entry.pack(side="left", padx=(0, 8), ipady=6)
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_resources())
        self.search_entry.bind("<FocusIn>", self.clear_search_placeholder)
        self.search_entry.bind("<FocusOut>", self.restore_search_placeholder)
        self.set_search_placeholder()

        clear_btn = tk.Button(
            search_wrap,
            text="Limpiar",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            bd=0,
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.clear_search
        )
        clear_btn.pack(side="left", padx=(10, 0))

        canvas_wrap = tk.Frame(content, bg=COLORS["bg"])
        canvas_wrap.pack(fill="both", expand=True, padx=22, pady=(0, 20))

        canvas = tk.Canvas(
            canvas_wrap,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0
        )

        scrollbar = tk.Scrollbar(
            canvas_wrap,
            orient="vertical",
            command=canvas.yview,
            bg=COLORS["panel"],
            troughcolor=COLORS["bg"],
            activebackground=COLORS["primary"],
            width=8
        )

        self.scroll_frame = tk.Frame(canvas, bg=COLORS["bg"])
        scroll_window = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        def update_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_scroll_frame(event):
            canvas.itemconfig(scroll_window, width=event.width)

        self.scroll_frame.bind("<Configure>", update_scrollregion)
        canvas.bind("<Configure>", resize_scroll_frame)

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.enable_mousewheel(canvas)

        for category in company.get("categories", []):
            self.create_category_section(
                self.scroll_frame,
                category,
                company.get("theme_color", COLORS["primary"])
            )

        self.update_results_label()

    def create_metric(self, parent, label, value, col):
        card = tk.Frame(
            parent,
            bg=COLORS["card"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        card.grid(row=0, column=col, padx=(0, 10), sticky="w")

        tk.Label(
            card,
            text=label,
            font=("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["muted"]
        ).pack(anchor="w", padx=12, pady=(10, 2))

        tk.Label(
            card,
            text=value,
            font=("Segoe UI", 14, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"]
        ).pack(anchor="w", padx=12, pady=(0, 10))

        self.add_card_hover(card)

    def create_category_section(self, parent, category, theme_color):
        section = tk.Frame(parent, bg=COLORS["bg"])
        section.pack(fill="x", pady=10)

        title_label = tk.Label(
            section,
            text=category.get("name", "Categoría"),
            font=("Segoe UI", 15, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["text"]
        )
        title_label.pack(anchor="w")

        desc_label = tk.Label(
            section,
            text=category.get("description", ""),
            font=("Segoe UI", 10),
            bg=COLORS["bg"],
            fg=COLORS["muted"]
        )
        desc_label.pack(anchor="w", pady=(4, 10))

        grid = tk.Frame(section, bg=COLORS["bg"])
        grid.pack(fill="x")

        for i in range(2):
            grid.grid_columnconfigure(i, weight=1)

        section_data = {
            "frame": section,
            "grid": grid,
            "cards": [],
            "title": title_label,
            "desc": desc_label
        }
        self.category_sections.append(section_data)

        for idx, resource in enumerate(category.get("resources", [])):
            row, col = divmod(idx, 2)
            card = self.create_resource_card(grid, resource, theme_color)
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            section_data["cards"].append(card)

    def create_resource_card(self, parent, resource, theme_color):
        card = tk.Frame(
            parent,
            bg=COLORS["card"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )

        top_line = tk.Frame(card, bg=COLORS["card"])
        top_line.pack(fill="x", padx=16, pady=(14, 6))

        resource_type = resource.get("type", "folder")
        icon = TYPE_ICONS.get(resource_type, "📁")

        tk.Label(
            top_line,
            text=icon,
            font=("Segoe UI Emoji", 14),
            bg=COLORS["card"],
            fg=COLORS["text"]
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            top_line,
            text=resource.get("name", "Recurso"),
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"]
        ).pack(side="left")

        tk.Label(
            card,
            text=resource.get("path", ""),
            font=("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            justify="left",
            wraplength=520
        ).pack(anchor="w", padx=16)

        status_frame = tk.Frame(card, bg=COLORS["card"])
        status_frame.pack(fill="x", padx=16, pady=(12, 8))

        status_canvas = tk.Canvas(
            status_frame,
            width=16,
            height=16,
            bg=COLORS["card"],
            highlightthickness=0
        )
        status_canvas.pack(side="left")

        initial_status = "web" if resource_type == "web" else "unknown"
        initial_color = COLORS["primary"] if resource_type == "web" else COLORS["warning"]

        dot = status_canvas.create_oval(
            3, 3, 13, 13,
            fill=initial_color,
            outline=initial_color
        )

        status_label = tk.Label(
            status_frame,
            text=STATUS_TEXT[initial_status],
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["card"],
            fg=initial_color
        )
        status_label.pack(side="left", padx=(5, 0))

        actions = tk.Frame(card, bg=COLORS["card"])
        actions.pack(fill="x", padx=16, pady=(4, 14))

        tk.Button(
            actions,
            text="Abrir",
            font=("Segoe UI", 9, "bold"),
            bg=theme_color,
            fg="white",
            activebackground=COLORS["primary_hover"],
            activeforeground="white",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            command=lambda r=resource: self.open_resource(r)
        ).pack(side="left", padx=(0, 8))

        if resource_type == "web":
            tk.Button(
                actions,
                text="Copiar link",
                font=("Segoe UI", 9),
                bg=COLORS["input"],
                fg=COLORS["text"],
                bd=0,
                padx=14,
                pady=8,
                cursor="hand2",
                command=lambda p=resource.get("path", ""): self.copy_to_clipboard(p)
            ).pack(side="left")
        else:
            tk.Button(
                actions,
                text="Verificar",
                font=("Segoe UI", 9),
                bg=COLORS["input"],
                fg=COLORS["text"],
                bd=0,
                padx=14,
                pady=8,
                cursor="hand2",
                command=lambda r=resource, c=status_canvas, d=dot, l=status_label: self.check_resource(r, c, d, l)
            ).pack(side="left")

        card._resource = resource
        card._status_canvas = status_canvas
        card._status_dot = dot
        card._status_label = status_label
        card._search_text = f"{resource.get('name', '')} {resource.get('path', '')}".lower()

        self.resource_cards.append(card)
        self.add_card_hover(card)
        return card

    def update_status_ui(self, canvas, dot, label, status):
        color_map = {
            "unknown": COLORS["warning"],
            "checking": COLORS["warning"],
            "online": COLORS["success"],
            "offline": COLORS["danger"],
            "web": COLORS["primary"]
        }
        color = color_map.get(status, COLORS["warning"])
        canvas.itemconfig(dot, fill=color, outline=color)
        label.config(text=STATUS_TEXT.get(status, "Sin verificar"), fg=color)

    def check_resource(self, resource, status_canvas, status_dot, status_label):
        if self.is_busy:
            return

        path = resource.get("path", "").strip()
        resource_type = resource.get("type", "folder")

        if resource_type == "web":
            return

        self.update_status_ui(status_canvas, status_dot, status_label, "checking")

        def worker():
            host = get_host_from_unc(path)
            ok = False

            if host:
                ok = can_ping(host) or can_resolve(host)

            if not ok and os.path.exists(path):
                ok = True

            final_status = "online" if ok else "offline"
            write_log(f"VERIFICACION | {resource.get('name')} | {path} | {final_status}")
            self.root.after(
                0,
                lambda: self.update_status_ui(status_canvas, status_dot, status_label, final_status)
            )

        threading.Thread(target=worker, daemon=True).start()

    def check_all_resources(self):
        if self.is_busy:
            return

        self.is_busy = True

        def worker():
            for card in self.resource_cards:
                resource = card._resource
                if resource.get("type", "folder") == "web":
                    continue

                path = resource.get("path", "").strip()
                host = get_host_from_unc(path)
                ok = False

                self.root.after(
                    0,
                    lambda c=card: self.update_status_ui(
                        c._status_canvas,
                        c._status_dot,
                        c._status_label,
                        "checking"
                    )
                )

                if host:
                    ok = can_ping(host) or can_resolve(host)

                if not ok and os.path.exists(path):
                    ok = True

                final_status = "online" if ok else "offline"
                write_log(f"VERIFICACION | {resource.get('name')} | {path} | {final_status}")

                self.root.after(
                    0,
                    lambda c=card, s=final_status: self.update_status_ui(
                        c._status_canvas,
                        c._status_dot,
                        c._status_label,
                        s
                    )
                )

            self.root.after(0, lambda: setattr(self, "is_busy", False))

        threading.Thread(target=worker, daemon=True).start()

    def open_resource(self, resource):
        if self.is_busy:
            return

        path = resource.get("path", "").strip()
        resource_type = resource.get("type", "folder")
        company_name = self.selected_company.get("name", "-") if self.selected_company else "-"

        def worker():
            try:
                if resource_type == "web":
                    webbrowser.open(path)
                    write_log(f"ABRIR WEB | {company_name} | {resource.get('name')} | {path}")
                    return

                os.startfile(path)
                write_log(f"ABRIR RUTA | {company_name} | {resource.get('name')} | {path}")

            except Exception as e:
                write_log(f"ERROR ABRIR | {company_name} | {resource.get('name')} | {path} | {e}")
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error",
                        f"No se pudo abrir:\n{path}\n\nDetalle: {e}"
                    )
                )

        threading.Thread(target=worker, daemon=True).start()

    def open_all_resources(self):
        if self.is_busy:
            return

        confirm = messagebox.askyesno("Confirmación", "¿Deseas abrir todos los recursos de esta empresa?")
        if not confirm:
            return

        self.is_busy = True

        def worker():
            for card in self.resource_cards:
                resource = card._resource
                path = resource.get("path", "").strip()
                resource_type = resource.get("type", "folder")
                company_name = self.selected_company.get("name", "-") if self.selected_company else "-"

                try:
                    if resource_type == "web":
                        webbrowser.open(path)
                        write_log(f"ABRIR WEB | {company_name} | {resource.get('name')} | {path}")
                    else:
                        os.startfile(path)
                        write_log(f"ABRIR RUTA | {company_name} | {resource.get('name')} | {path}")
                except Exception as e:
                    write_log(f"ERROR ABRIR | {company_name} | {resource.get('name')} | {path} | {e}")

            self.root.after(0, lambda: setattr(self, "is_busy", False))

        threading.Thread(target=worker, daemon=True).start()

    def clear_search(self):
        self.search_var.set("")
        self.set_search_placeholder()
        self.filter_resources()

    def update_results_label(self, visible_count=None):
        if self.results_label is None:
            return

        if visible_count is None:
            visible_count = len(self.resource_cards)

        text = f"{visible_count} resultado" if visible_count == 1 else f"{visible_count} resultados"
        self.results_label.config(text=text)

    def filter_resources(self):
        search = self.get_search_text()
        total_visible = 0

        for section in self.category_sections:
            matching_cards = [
                card for card in section["cards"]
                if not search or search in card._search_text
            ]

            for card in section["cards"]:
                card.grid_forget()

            if matching_cards:
                section["frame"].pack(fill="x", pady=10)

                for index, card in enumerate(matching_cards):
                    row, col = divmod(index, 2)
                    card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)

                total_visible += len(matching_cards)
            else:
                section["frame"].pack_forget()

        self.update_results_label(total_visible)


if __name__ == "__main__":
    root = tk.Tk()
    app = OpenDeskApp(root)
    root.mainloop()