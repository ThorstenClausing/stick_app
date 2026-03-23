# -*- coding: utf-8 -*-
"""
Tkinter-based GUI for the Embroidery App.
Handles user interaction, localization, and image display.
"""

import tkinter as tk
from tkinter import ttk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from os import path, makedirs
import json
from PIL import ImageTk, Image
import numpy as np
import embroidery_logic as el

CONFIG_FILE = "config/stick_settings.json"
LOCALES_DIR = "config"

class StickApp(tk.Frame):
    
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(fill="both", expand=True)
        
        # Application State
        self.input_path = None
        self.current_pattern = None
        self.edit_mode = tk.StringVar(value="none")
        self.history = []
        self.selected_color_idx = 255
        self.palette_window = None
        self.zoom_level = 1.0
        self.base_size = (0, 0)
        self.texts = {}
        self.lang_code = tk.StringVar(value="de")
        
        # Menu Reference Dictionary
        self.menu_refs = {}

        # Config Variables
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
            "num_objects": 3,
            "model_version": "Version 1",
            "paper_size": "A4 Portrait",
            "language": "de"
        }

        self.load_settings()
        self.load_translations()
        self.setup_ui()
        self.bind_shortcuts()

    def setup_ui(self):
        """
        Initializes all UI components.
        """
        self.create_menubar()
        self.create_canvas_area()
        self.refresh_ui_text()

    def load_translations(self):
        """
        Loads JSON locale file based on current setting.
        """
        lang = self.settings["language"].get()
        fpath = path.join("config", f"{lang}.json")
        try:
            if path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    self.texts = json.load(f)
            else:
                self.texts = {} # Fallback logic could be added here
        except Exception as e:
            print(f"Translation error: {e}")

    def create_menubar(self):
        """
        Creates the menu and stores references for dynamic state updates.
        """
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # File Menu
        file_m = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=file_m) # Label set in refresh_ui_text
        self.menu_refs['file_cascade'] = self.menubar.index("end")
        
        file_m.add_command(command=self.load_image)
        self.menu_refs['load'] = file_m.index("end")
        file_m.add_command(command=self.save_pattern, state="disabled")
        self.menu_refs['save'] = file_m.index("end")
        file_m.add_separator()
        file_m.add_command(command=self.master.destroy)
        self.menu_refs['exit'] = file_m.index("end")
        self.menu_refs['file_menu'] = file_m

        # Pattern Menu
        pat_m = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=pat_m)
        self.menu_refs['pattern_cascade'] = self.menubar.index("end")
        
        self.menu_refs['gen'] = pat_m.add_command(command=lambda: self.process(False), state="disabled")
        self.menu_refs['gen_nobg'] = pat_m.add_command(command=lambda: self.process(True), state="disabled")
        self.menu_refs['edit'] = pat_m.add_command(command=self.open_palette, state="disabled")
        self.menu_refs['undo'] = pat_m.add_command(command=self.undo, state="disabled", accelerator="Ctrl+Z")
        self.menu_refs['pattern_menu'] = pat_m

        # View Menu
        view_m = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=view_m)
        self.menu_refs['view_cascade'] = self.menubar.index("end")
        
        self.menu_refs['clear'] = view_m.add_command(command=self.clear_all, state="disabled")
        zoom_m = tk.Menu(view_m, tearoff=0)
        view_m.add_cascade(menu=zoom_m)
        zoom_m.add_command(command=lambda: self.change_zoom(0.2))
        zoom_m.add_command(command=lambda: self.change_zoom(-0.2))
        zoom_m.add_command(command=lambda: self.change_zoom(0, True))
        self.menu_refs['view_menu'] = view_m
        self.menu_refs['zoom_menu'] = zoom_m

        # Settings
        set_m = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=set_m)
        self.menu_refs['settings_cascade'] = self.menubar.index("end")
        set_m.add_command(command=self.open_settings)
        self.menu_refs['settings_menu'] = set_m

    def refresh_ui_text(self):
        """
        Updates all UI labels from the translation dictionary.
        """
        t = self.texts
        m = self.menu_refs
        
        # Update Menu Labels
        self.menubar.entryconfig(m['file_cascade'], label=t.get("file", "File"))
        m['file_menu'].entryconfig(m['load'], label=t.get("load_image", "Load..."))
        m['file_menu'].entryconfig(m['save'], label=t.get("save_pattern", "Save..."))
        m['file_menu'].entryconfig(m['exit'], label=t.get("exit", "Exit"))

        self.menubar.entryconfig(m['pattern_cascade'], label=t.get("pattern", "Pattern"))
        m['pattern_menu'].entryconfig(0, label=t.get("gen_pattern", "Generate"))
        m['pattern_menu'].entryconfig(1, label=t.get("gen_no_bg", "Gen (No Background)"))
        m['pattern_menu'].entryconfig(2, label=t.get("edit_pattern", "Edit"))
        m['pattern_menu'].entryconfig(3, label=t.get("undo", "Undo"))

        self.menubar.entryconfig(m['view_cascade'], label=t.get("view", "View"))
        m['view_menu'].entryconfig(0, label=t.get("clear", "Clear"))
        m['view_menu'].entryconfig(2, label=t.get("zoom", "Zoom"))
        m['zoom_menu'].entryconfig(0, label=t.get("zoom_in"))
        m['zoom_menu'].entryconfig(1, label=t.get("zoom_out"))
        m['zoom_menu'].entryconfig(2, label=t.get("zoom_std"))

        self.menubar.entryconfig(m['settings_cascade'], label=t.get("settings", "Settings"))
        m['settings_menu'].entryconfig(0, label=t.get("params", "Parameters..."))
        
        # Update Palette window if open
        if self.palette_window and self.palette_window.winfo_exists():
            self.palette_window.title(t.get("color_sel"))

    def create_canvas_area(self):
        """
        Sets up the scrollable canvas for image display.
        """
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(frame, bg="gray80", highlightthickness=0)
        v_scroll = tk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        h_scroll = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        h_scroll.pack(side="bottom", fill="x")

        self.canvas.bind("<Button-1>", self.handle_click)
        self.canvas.bind("<B1-Motion>", lambda e: self.handle_click(e, motion=True))

    def load_image(self):
        """
        Handles image file selection.
        """
        self.stop_editing()
        fpath = fd.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if fpath:
            self.input_path = fpath
            self.zoom_level = 1.0
            self.current_pattern = None
            self.history = []
            self.display_image(Image.open(fpath))
            
            # Update menu states
            self.menu_refs['pattern_menu'].entryconfig(0, state="normal")
            self.menu_refs['pattern_menu'].entryconfig(1, state="normal")
            self.menu_refs['view_menu'].entryconfig(0, state="normal")

    def display_image(self, pil_img):
        """
        Resizes and renders the image on the canvas.
        """
        if self.zoom_level == 1.0:
            # Set base size for fitting 
            ratio = min(1000 / pil_img.width, 600 / pil_img.height)
            self.base_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))

        w = int(self.base_size[0] * self.zoom_level)
        h = int(self.base_size[1] * self.zoom_level)
        
        resized = pil_img.resize((w, h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)
        
        self.canvas.delete("all")
        cx = max(w, self.canvas.winfo_width()) // 2
        cy = max(h, self.canvas.winfo_height()) // 2
        self.image_item = self.canvas.create_image(cx, cy, image=self.photo)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def process(self, remove_bg):
        """
        Runs the background removal and pattern generation logic.
        """
        if not self.input_path: return
        self.stop_editing()
        self.master.config(cursor="watch")
        self.master.update()
        
        try:
            img = Image.open(self.input_path)
            if remove_bg:
                img, success = el.remove_background(
                    img, 
                    self.settings['score_threshold'].get(),
                    self.settings['num_objects'].get(),
                    self.settings['model_version'].get()
                )
                if not success and not mb.askyesno(self.texts.get("msg_bg_title"), 
                                                   self.texts.get("msg_no_obj_text", "No objects found. Continue?")):
                    return

            self.current_pattern = el.generate_embroidery_pattern(
                img,
                self.settings['kmeans_n_clusters'].get(),
                self.settings['crosses_x'].get()
            )
            self.display_image(self.current_pattern['pil_image'])
            self.menu_refs['pattern_menu'].entryconfig(2, state="normal")
            self.menu_refs['file_menu'].entryconfig(1, state="normal")
            
        except Exception as e:
            mb.showerror("Error", str(e))
        finally:
            self.master.config(cursor="")

    def handle_click(self, event, motion=False):
        """
        Maps canvas mouse coordinates to pattern grid coordinates.
        """
        if not self.current_pattern or self.edit_mode.get() != "paint":
            return
            
        # Get relative position within image
        bbox = self.canvas.bbox(self.image_item)
        x = self.canvas.canvasx(event.x) - bbox[0]
        y = self.canvas.canvasy(event.y) - bbox[1]
        img_w, img_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        if 0 <= x < img_w and 0 <= y < img_h:
            grid_h, grid_w = self.current_pattern['matrix'].shape
            col = int((x / img_w) * grid_w)
            row = int((y / img_h) * grid_h)
            self.apply_edit(row, col, push_history=not motion)

    def apply_edit(self, row, col, push_history=True):
        """
        Modifies the grid and updates the view.
        """
        pat = self.current_pattern
        if pat['matrix'][row, col] == self.selected_color_idx:
            return

        if push_history:
            # Simple deep copy for undo
            self.history.append({
                'matrix': pat['matrix'].copy(),
                'pil_image': pat['pil_image'].copy(),
                'cluster_centers': pat['cluster_centers'].copy()
            })
            if len(self.history) > 50: self.history.pop(0)
            self.menu_refs['pattern_menu'].entryconfig(3, state="normal")

        self.current_pattern = el.update_pattern_at_coord(pat, row, col, self.selected_color_idx)
        self.display_image(self.current_pattern['pil_image'])

    def undo(self, event=None):
        if self.history:
            self.current_pattern = self.history.pop()
            self.display_image(self.current_pattern['pil_image'])
            if not self.history:
                self.menu_refs['pattern_menu'].entryconfig(3, state="disabled")

    def open_palette(self):
        """
        Creates a floating window for thread color selection.
        """
        if self.palette_window: self.palette_window.destroy()
        
        self.palette_window = tk.Toplevel(self)
        self.palette_window.title(self.texts.get("color_sel", "Colors"))
        self.palette_window.geometry("200x400")
        self.palette_window.attributes("-topmost", True)
        self.palette_window.protocol("WM_DELETE_WINDOW", self.stop_editing)
        
        # Color List with Scrollbar
        canvas = tk.Canvas(self.palette_window)
        frame = tk.Frame(canvas)
        scr = tk.Scrollbar(self.palette_window, command=canvas.yview)
        canvas.configure(yscrollcommand=scr.set)
        
        scr.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0,0), window=frame, anchor="nw")

        def select(idx):
            self.selected_color_idx = idx
            self.edit_mode.set("paint")
            self.master.config(cursor="pencil")

        tk.Button(frame, 
                  text=self.texts.get("eraser"), 
                  bg="white", 
                  command=lambda: select(255)).pack(fill="x")
        
        centers = self.current_pattern['cluster_centers']
        seen_colors = set()
        
        for i, color in enumerate(centers):
            rgb_tuple = tuple(color.astype(int))
            # Only add the button if this RGB value hasn't been displayed yet
            if rgb_tuple not in seen_colors:
                seen_colors.add(rgb_tuple)
                rgb_hex = '#%02x%02x%02x' % rgb_tuple
                text_col = "white" if np.mean(color) < 128 else "black"
                tk.Button(frame, text=f"ID {i}", bg=rgb_hex, fg=text_col, 
                          command=lambda idx=i: select(idx), height=2).pack(fill="x", pady=2)

        frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def change_zoom(self, delta, reset=False):
        self.zoom_level = 1.0 if reset else max(1.0, self.zoom_level + delta)
        img = self.current_pattern['pil_image'] if self.current_pattern else Image.open(self.input_path)
        self.display_image(img)

    def clear_all(self):
        self.stop_editing()
        self.canvas.delete("all")
        self.input_path = None
        self.current_pattern = None
        self.master.config(cursor="")
        self.zoom_level = 1.0
        
        m = self.menu_refs
        
        # Using indices based on create_menubar order:
        # pattern_menu: 0=Generate, 1=No BG, 2=Edit, 3=Undo
        m['pattern_menu'].entryconfig(0, state="disabled")
        m['pattern_menu'].entryconfig(1, state="disabled")
        m['pattern_menu'].entryconfig(2, state="disabled")
        m['pattern_menu'].entryconfig(3, state="disabled")
        
        # file_menu: 1=Save Pattern
        m['file_menu'].entryconfig(1, state="disabled")
        
        # view_menu: 0=Clear Display
        m['view_menu'].entryconfig(0, state="disabled")

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
                if choice == t.get("paper_a4_p"): p_size = el.A4
                elif choice == t.get("paper_a4_l"): p_size = el.landscape(el.A4)
                elif choice == t.get("paper_a3_p"): p_size = el.A3
                elif choice == t.get("paper_a3_l"): p_size = el.landscape(el.A3)
                else: p_size = el.A4
                
                el.save_as_pdf(output_path, 
                               self.current_pattern, 
                               f"{pattern_label}: {base_name}", 
                               legend_text=legend_label,
                               pagesize=p_size)
            else:
                el.save_as_jpeg(output_path, self.current_pattern)
            mb.showinfo(t.get("msg_success_title"), t.get("msg_save_success"))

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

    def bind_shortcuts(self):
        self.master.bind("<Control-z>", self.undo)
        
    def reset_to_defaults(self):
        t = self.texts
        if mb.askyesno(t.get("msg_reset_title"), t.get("msg_reset_text")):
            for key, val in self.defaults.items():
                if key == "paper_size":
                    self.settings[key].set(t.get("paper_a4_p"))
                else:
                    self.settings[key].set(val)
            self.save_settings_to_file()
            
    def save_settings_to_file(self):
        data = {k: v.get() for k, v in self.settings.items()}
        makedirs(path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
        
        # Reload translations and refresh UI immediately
        self.load_translations()
        self.refresh_ui_text()
        
    def stop_editing(self):
        """
        Terminates paint mode and closes palette window.
        """
        self.edit_mode.set("none")
        self.master.config(cursor="")
        if self.palette_window and self.palette_window.winfo_exists():
            self.palette_window.destroy()
        self.palette_window = None
