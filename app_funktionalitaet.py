# -*- coding: utf-8 -*-
"""
This file contains the description (class) of the GUI of the stick app.

@author: Thorsten
"""

import tkinter as tk
import tkinter.filedialog as fd
from tkinter import ttk
import tkinter.messagebox as mb
from os import path, makedirs
from PIL import ImageTk, Image
import numpy as np
import json
import stick_funktionalitaet as sf

CONFIG_FILE = "config/stick_settings.json"
LOCALES_DIR = "config"

class StickApp(tk.Frame):
    
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(fill="both", expand=True)
        
        # State
        self.input_path = None
        self.current_pattern = None
        self.edit_mode = tk.StringVar(value="none") 
        self.history = [] 
        self.selected_color_index = 255
        self.palette_window = None
        self.zoom_level = 1.0
        self.base_display_size = (0, 0)
        
        # Translations
        self.texts = {}
        self.lang_code = tk.StringVar(value="de")

        # Settings
        self.settings = {
            "crosses_x": tk.IntVar(),
            "kmeans_n_clusters": tk.IntVar(),
            "score_threshold": tk.DoubleVar(),
            "num_objects": tk.IntVar(),
            "model_version": tk.StringVar(),
            "paper_size": tk.StringVar(),
            "language": self.lang_code
        }
        
        self.defaults = {
            "crosses_x": 150,
            "kmeans_n_clusters": 20,
            "score_threshold": 0.75,
            "num_objects": 1,
            "model_version": "Version 1",
            "paper_size": "A4 hoch",
            "language": "de"
        }

        self.load_settings()
        self.load_translations()
        
        self.create_menubar()
        self.create_canvas_area()
        self.refresh_ui_text() # Initial text application

        self.master.bind("<Control-z>", self.undo_action)
        self.master.bind("<Control-Z>", self.undo_action)
        
    def load_translations(self):
        lang = self.lang_code.get()
        lang_path = path.join(LOCALES_DIR, f"{lang}.json")
        try:
            with open(lang_path, "r", encoding="utf-8") as f:
                self.texts = json.load(f)
        except Exception as e:
            print(f"Error loading translation {lang}: {e}")
            # Fallback to hardcoded defaults or German if file missing
            if lang != "de":
                self.lang_code.set("de")
                self.load_translations()
                
    def refresh_ui_text(self):
        """
        Updates all strings in the UI based on current translations.
        """
        t = self.texts
        
        # Menu Titles
        self.menubar.entryconfig(1, label=t.get("file", "File"))
        self.menubar.entryconfig(2, label=t.get("pattern", "Pattern"))
        self.menubar.entryconfig(3, label=t.get("view", "View"))
        self.menubar.entryconfig(4, label=t.get("settings", "Settings"))

        # File Menu Items
        self.datei_menu.entryconfig(0, label=t.get("load_image"))
        self.datei_menu.entryconfig(1, label=t.get("save_pattern"))
        self.datei_menu.entryconfig(3, label=t.get("exit"))

        # Pattern Menu Items
        self.stick_menu.entryconfig(0, label=t.get("gen_pattern"))
        self.stick_menu.entryconfig(1, label=t.get("gen_no_bg"))
        self.stick_menu.entryconfig(2, label=t.get("edit_pattern"))
        self.stick_menu.entryconfig(3, label=t.get("undo"))

        # View Menu
        self.ansicht_menu.entryconfig(0, label=t.get("clear"))
        self.ansicht_menu.entryconfig(2, label=t.get("zoom"))
        self.zoom_menu.entryconfig(0, label=t.get("zoom_in"))
        self.zoom_menu.entryconfig(1, label=t.get("zoom_out"))
        self.zoom_menu.entryconfig(2, label=t.get("zoom_std"))

        # Settings Menu
        self.settings_menu.entryconfig(0, label=t.get("params"))

        # Update Palette window if open
        if self.palette_window and self.palette_window.winfo_exists():
            self.palette_window.title(t.get("color_sel"))
        
    def load_settings(self):
        data = self.defaults.copy()
        if path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    data.update(loaded)
            except Exception: pass
        for key, val in data.items():
            if key in self.settings:
                self.settings[key].set(val)

    def save_settings_to_file(self):
        data = {k: v.get() for k, v in self.settings.items()}
        makedirs(path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
        
        # Reload translations and refresh UI immediately
        self.load_translations()
        self.refresh_ui_text()

    def open_settings(self):
        t = self.texts
        settings_win = tk.Toplevel(self)
        settings_win.title(t.get("params"))
        settings_win.geometry("400x600")
        settings_win.grab_set()
        container = ttk.Frame(settings_win, padding=20)
        container.pack(fill="both", expand=True)

        def add_row(label_key, var, widget_type="entry", values=None):
            ttk.Label(container, text=t.get(label_key)).pack(anchor="w")
            if widget_type == "entry":
                # Ensure float values use '.' by forcing string conversion if needed
                ent = ttk.Entry(container, textvariable=var)
                ent.pack(fill="x", pady=(0, 10))
            elif widget_type == "combo":
                ttk.Combobox(container, textvariable=var, values=values, state="readonly").pack(fill="x", pady=(0, 10))

        add_row("crosses_x", self.settings["crosses_x"])
        add_row("colors", self.settings["kmeans_n_clusters"])
        add_row("ai_model", self.settings["model_version"], "combo", ["Version 1", "Version 2"])
        add_row("threshold", self.settings["score_threshold"])
        add_row("objects", self.settings["num_objects"])
        
        # Localized Paper Sizes
        paper_options = [t.get("paper_a4_p"), t.get("paper_a4_l"), t.get("paper_a3_p"), t.get("paper_a3_l")]
        # If the current value is German (default), try to translate it to the current language
        curr_p = self.settings["paper_size"].get()
        if curr_p not in paper_options:
             # Fallback: if we just switched languages, reset to A4 Portrait in new language
             self.settings["paper_size"].set(t.get("paper_a4_p"))
             
        add_row("paper", self.settings["paper_size"], "combo", paper_options)
        
        ttk.Label(container, text=t.get("language"), font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10, 0))
        lang_map = {"Deutsch": "de", "English": "en", "Français": "fr", "Nederlands": "nl"}
        inv_lang_map = {v: k for k, v in lang_map.items()}
        
        lang_var = tk.StringVar(value=inv_lang_map.get(self.lang_code.get(), "English"))
        lang_cb = ttk.Combobox(container, textvariable=lang_var, values=list(lang_map.keys()), state="readonly")
        lang_cb.pack(fill="x", pady=(0, 20))

        def save_and_close():
            self.lang_code.set(lang_map[lang_var.get()])
            self.save_settings_to_file()
            settings_win.destroy()

        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text=t.get("save"), command=save_and_close).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=t.get("reset"), command=self.reset_to_defaults).pack(side="left", padx=5)
        
    def reset_to_defaults(self):
        t = self.texts
        if mb.askyesno(t.get("msg_reset_title"), t.get("msg_reset_text")):
            for key, val in self.defaults.items():
                if key == "paper_size":
                    self.settings[key].set(t.get("paper_a4_p"))
                else:
                    self.settings[key].set(val)
            self.save_settings_to_file()
        
    def create_canvas_area(self):
        # Frame to hold Canvas and Scrollbars
        self.canvas_frame = tk.Frame(self)
        self.canvas_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.canvas = tk.Canvas(self.canvas_frame, bg="gray70", highlightthickness=0)
        
        self.v_scroll = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.h_scroll = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Button-1>", lambda e: self.on_canvas_interaction(e, is_motion=False))
        self.canvas.bind("<B1-Motion>", lambda e: self.on_canvas_interaction(e, is_motion=True))

    def create_menubar(self):
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        self.datei_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Datei", menu=self.datei_menu)
        self.datei_menu.add_command(label="...", command=self.load_image)
        self.datei_menu.add_command(label="...", command=self.save_pattern, state="disabled")
        self.datei_menu.add_separator()
        self.datei_menu.add_command(label="...", command=self.master.destroy)

        self.stick_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Stickmuster", menu=self.stick_menu)
        self.stick_menu.add_command(label="...", command=lambda: self.process(False), state="disabled")
        self.stick_menu.add_command(label="...", command=lambda: self.process(True), state="disabled")
        self.stick_menu.add_command(label="...", command=self.enable_edit_mode, state="disabled")
        self.stick_menu.add_command(label="...", command=self.undo_action, state="disabled", accelerator="Ctrl+Z")

        self.ansicht_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Ansicht", menu=self.ansicht_menu)
        self.ansicht_menu.add_command(label="...", command=self.clear_display, state="disabled")
        self.ansicht_menu.add_separator()
        self.zoom_menu = tk.Menu(self.ansicht_menu, tearoff=0)
        self.ansicht_menu.add_cascade(label="Zoom", menu=self.zoom_menu)
        self.zoom_menu.add_command(label="...", command=lambda: self.change_zoom(0.2))
        self.zoom_menu.add_command(label="...", command=lambda: self.change_zoom(-0.2))
        self.zoom_menu.add_command(label="...", command=lambda: self.change_zoom(0, reset=True))

        self.settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Einstellungen", menu=self.settings_menu)
        self.settings_menu.add_command(label="...", command=self.open_settings)

    def stop_editing(self):
        """
        Terminates paint mode and closes palette window.
        """
        self.edit_mode.set("none")
        self.master.config(cursor="")
        if self.palette_window and self.palette_window.winfo_exists():
            self.palette_window.destroy()
        self.palette_window = None

    def clear_display(self):
        self.stop_editing()
        self.canvas.delete("all")
        self.input_path = None
        self.current_pattern = None
        self.zoom_level = 1.0
        
        # Using indices based on create_menubar order:
        # stick_menu: 0=Generate, 1=No BG, 2=Edit, 3=Undo
        self.stick_menu.entryconfig(0, state="disabled")
        self.stick_menu.entryconfig(1, state="disabled")
        self.stick_menu.entryconfig(2, state="disabled")
        self.stick_menu.entryconfig(3, state="disabled")
        
        # datei_menu: 1=Save Pattern
        self.datei_menu.entryconfig(1, state="disabled")
        
        # ansicht_menu: 0=Clear Display
        self.ansicht_menu.entryconfig(0, state="disabled")

    def change_zoom(self, delta, reset=False):
        if not self.input_path: return
        if reset:
            self.zoom_level = 1.0
        else:
            self.zoom_level = max(1.0, self.zoom_level + delta)
        
        img = self.current_pattern['pil_image'] if self.current_pattern else Image.open(self.input_path)
        self.display_image(img)

    def enable_edit_mode(self):
        if not self.current_pattern: return
        if self.palette_window and self.palette_window.winfo_exists():
            self.palette_window.lift()
            return

        self.palette_window = tk.Toplevel(self)
        self.palette_window.title("Farbauswahl")
        self.palette_window.geometry("250x400")
        self.palette_window.attributes("-topmost", True)
        self.palette_window.protocol("WM_DELETE_WINDOW", self.stop_editing)

        lbl = tk.Label(self.palette_window, text="Farbe wählen:", font=("Helvetica", 10, "bold"))
        lbl.pack(pady=10)

        container = tk.Frame(self.palette_window)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        canvas_scroll = tk.Canvas(container, width=200)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas_scroll.yview)
        scroll_frame = tk.Frame(canvas_scroll)

        scroll_frame.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
        canvas_scroll.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def select_color(idx):
            self.selected_color_index = idx
            self.edit_mode.set("paint")
            self.master.config(cursor="pencil")
            lbl.config(text=f"Gewählt: {'Radierer' if idx==255 else f'Farbe ID {idx}'}")

        # Add Eraser
        tk.Button(scroll_frame, text="Radierer (Weiß)", bg="white", command=lambda: select_color(255), height=2).pack(fill="x", pady=2)
        
        # Add Unique Colors only
        centers = self.current_pattern['cluster_centers']
        seen_colors = set()
        
        for i, color in enumerate(centers):
            rgb_tuple = tuple(color.astype(int))
            # Only add the button if this RGB value hasn't been displayed yet
            if rgb_tuple not in seen_colors:
                seen_colors.add(rgb_tuple)
                rgb_hex = '#%02x%02x%02x' % rgb_tuple
                text_col = "white" if np.mean(color) < 128 else "black"
                tk.Button(scroll_frame, text=f"Farbe ID {i}", bg=rgb_hex, fg=text_col, 
                          command=lambda idx=i: select_color(idx), height=2).pack(fill="x", pady=2)
                
    def display_image(self, pil_img):
        # Calculate base size if not set (first load)
        if self.zoom_level == 1.0:
            display_h = 600
            display_w = int(pil_img.width * (display_h / pil_img.height))
            if display_w > 1000:
                display_w = 1000
                display_h = int(pil_img.height * (display_w / pil_img.width))
            self.base_display_size = (display_w, display_h)

        # Apply zoom
        z_w = int(self.base_display_size[0] * self.zoom_level)
        z_h = int(self.base_display_size[1] * self.zoom_level)
            
        img_resized = pil_img.resize((z_w, z_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img_resized)
        
        self.canvas.delete("all")
        # Center the image in the canvas if image is smaller than viewport
        c_w = max(z_w, self.canvas.winfo_width())
        c_h = max(z_h, self.canvas.winfo_height())
        
        self.image_item = self.canvas.create_image(c_w // 2, c_h // 2, image=self.photo)
        self.canvas.config(scrollregion=(0, 0, c_w, c_h))

    def on_canvas_interaction(self, event, is_motion=False):
        if not self.current_pattern or self.edit_mode.get() != "paint": 
            return
        
        # Translate screen coordinates to canvas coordinates (accounting for scroll)
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        
        # Get image bounds on canvas
        bbox = self.canvas.bbox(self.image_item)
        if not bbox: return
        x1, y1, x2, y2 = bbox
        
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            # Map canvas coord to normalized 0.0 - 1.0 within image
            rel_x = (cx - x1) / (x2 - x1)
            rel_y = (cy - y1) / (y2 - y1)
            
            matrix = self.current_pattern['matrix']
            grid_h, grid_w = matrix.shape
            
            col = int(rel_x * grid_w)
            row = int(rel_y * grid_h)
            
            # Bounds check for safety
            col = min(max(0, col), grid_w - 1)
            row = min(max(0, row), grid_h - 1)
            
            self.modify_pattern(row, col, push_history=(not is_motion))

    def modify_pattern(self, row, col, push_history=True):
        if self.current_pattern['matrix'][row, col] == self.selected_color_index:
            return

        if push_history:
            state_snapshot = {
                "pil_image": self.current_pattern["pil_image"].copy(),
                "matrix": self.current_pattern["matrix"].copy(),
                "cluster_centers": self.current_pattern["cluster_centers"].copy()
            }
            self.history.append(state_snapshot)
            if len(self.history) > 50: self.history.pop(0)
            
            # Index 3 is "Undo action"
            self.stick_menu.entryconfig(3, state="normal")

        self.current_pattern = sf.update_pattern_at_coord(
            self.current_pattern, row, col, self.selected_color_index
        )
        self.display_image(self.current_pattern['pil_image'])

    def undo_action(self, event=None):
        if self.history:
            self.current_pattern = self.history.pop()
            self.display_image(self.current_pattern['pil_image'])
            if not self.history:
                # Index 3 is "Undo action"
                self.stick_menu.entryconfig(3, state="disabled")

    def load_image(self):
        path_selected = fd.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if path_selected:
            self.stop_editing()
            self.input_path = path_selected
            self.zoom_level = 1.0
            self.display_image(Image.open(self.input_path))
            self.current_pattern = None
            self.history = []
            
            # ansicht_menu: 0=Clear Display
            self.ansicht_menu.entryconfig(0, state="normal")
            
            # stick_menu: 0=Generate, 1=No BG, 2=Edit, 3=Undo
            self.stick_menu.entryconfig(0, state="normal")
            self.stick_menu.entryconfig(1, state="normal")
            self.stick_menu.entryconfig(2, state="disabled")
            self.stick_menu.entryconfig(3, state="disabled")
            
            # datei_menu: 1=Save Pattern
            self.datei_menu.entryconfig(1, state="disabled")
            
    def process(self, remove_bg):
        t = self.texts
        if not self.input_path: return
        self.stop_editing()
        img = Image.open(self.input_path)
        self.master.config(cursor="watch")
        self.master.update()
        
        try:
            processed_img = img
            if remove_bg:
                processed_img, success = sf.remove_background(
                    img, 
                    score_threshold=self.settings["score_threshold"].get(),
                    num_objects=self.settings["num_objects"].get(),
                    model_version=self.settings["model_version"].get())
                
                if not success:
                    self.master.config(cursor="")
                    answer = mb.askyesno(t.get("msg_bg_title"), t.get("msg_no_obj_text"))
                    if not answer: return 
                    self.master.config(cursor="watch")
                    self.master.update()

            self.current_pattern = sf.generate_embroidery_pattern(
                processed_img, 
                kmeans_n_clusters=self.settings["kmeans_n_clusters"].get(),
                crosses_x=self.settings["crosses_x"].get())
            
            self.display_image(self.current_pattern['pil_image'])
            self.stick_menu.entryconfig(2, state="normal")
            self.datei_menu.entryconfig(1, state="normal")
            
        except Exception as e:
            mb.showerror(t.get("msg_error_title"), f"{e}")
        finally:
            self.master.config(cursor="")

    def save_pattern(self):
        t = self.texts
        if not self.current_pattern: return
        base_name = path.basename(path.splitext(self.input_path)[0])
        
        file_prefix = t.get("pattern_file_prefix", "Pattern")
        pattern_label = t.get("embroidery_pattern", "Pattern")
        legend_label = t.get("color_legend", "Color Legend")
       
        output_path = fd.asksaveasfilename(
            initialfile=f"{file_prefix}_{base_name}",
            defaultextension=".pdf",
            filetypes=[(t.get("pdf_doc"), "*.pdf"), (t.get("jpeg_img"), "*.jpg")]
        )
        if output_path:
            if output_path.lower().endswith('.pdf'):
                choice = self.settings["paper_size"].get()
                if choice == t.get("paper_a4_p"): p_size = sf.A4
                elif choice == t.get("paper_a4_l"): p_size = sf.landscape(sf.A4)
                elif choice == t.get("paper_a3_p"): p_size = sf.A3
                elif choice == t.get("paper_a3_l"): p_size = sf.landscape(sf.A3)
                else: p_size = sf.A4
                
                sf.save_as_pdf(output_path, 
                               self.current_pattern, 
                               f"{pattern_label}: {base_name}", 
                               legend_text=legend_label,
                               pagesize=p_size)
            else:
                sf.save_as_jpeg(output_path, self.current_pattern)
            mb.showinfo(t.get("msg_success_title"), t.get("msg_save_success"))