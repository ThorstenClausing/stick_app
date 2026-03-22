# -*- coding: utf-8 -*-
"""
Tkinter-based GUI for the Embroidery App.
Handles user interaction, localization, and image display.
"""

import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from os import path
import json
from PIL import ImageTk, Image
import numpy as np
import embroidery_logic as el

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
        
        # Menu Reference Dictionary
        self.menu_refs = {}

        # Config Variables
        self.settings = {
            "crosses_x": tk.IntVar(value=150),
            "kmeans_n_clusters": tk.IntVar(value=20),
            "score_threshold": tk.DoubleVar(value=0.75),
            "num_objects": tk.IntVar(value=1),
            "model_version": tk.StringVar(value="Version 1"),
            "paper_size": tk.StringVar(value="A4 Portrait"),
            "language": tk.StringVar(value="en")
        }

        self.load_settings()
        self.load_translations()
        self.setup_ui()
        self.bind_shortcuts()

    def setup_ui(self):
        """Initializes all UI components."""
        self.create_menubar()
        self.create_canvas_area()
        self.refresh_ui_text()

    def load_translations(self):
        """Loads JSON locale file based on current setting."""
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
        """Creates the menu and stores references for dynamic state updates."""
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # File Menu
        file_m = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=file_m) # Label set in refresh_ui_text
        self.menu_refs['file_cascade'] = self.menubar.index("end")
        
        self.menu_refs['load'] = file_m.add_command(command=self.load_image)
        self.menu_refs['save'] = file_m.add_command(command=self.save_pattern, state="disabled")
        file_m.add_separator()
        self.menu_refs['exit'] = file_m.add_command(command=self.master.destroy)
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
        """Updates all UI labels from the translation dictionary."""
        t = self.texts
        m = self.menu_refs
        
        # Update Menu Labels
        self.menubar.entryconfig(m['file_cascade'], label=t.get("file", "File"))
        m['file_menu'].entryconfig(0, label=t.get("load_image", "Load..."))
        m['file_menu'].entryconfig(1, label=t.get("save_pattern", "Save..."))
        m['file_menu'].entryconfig(3, label=t.get("exit", "Exit"))

        self.menubar.entryconfig(m['pattern_cascade'], label=t.get("pattern", "Pattern"))
        m['pattern_menu'].entryconfig(0, label=t.get("gen_pattern", "Generate"))
        m['pattern_menu'].entryconfig(1, label=t.get("gen_no_bg", "Gen (No Background)"))
        m['pattern_menu'].entryconfig(2, label=t.get("edit_pattern", "Edit"))
        m['pattern_menu'].entryconfig(3, label=t.get("undo", "Undo"))

        self.menubar.entryconfig(m['view_cascade'], label=t.get("view", "View"))
        m['view_menu'].entryconfig(0, label=t.get("clear", "Clear"))
        m['view_menu'].entryconfig(2, label=t.get("zoom", "Zoom"))

        self.menubar.entryconfig(m['settings_cascade'], label=t.get("settings", "Settings"))
        m['settings_menu'].entryconfig(0, label=t.get("params", "Parameters..."))

    def create_canvas_area(self):
        """Sets up the scrollable canvas for image display."""
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
        """Handles image file selection."""
        fpath = fd.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if fpath:
            self.input_path = fpath
            self.zoom_level = 1.0
            self.current_pattern = None
            self.history = []
            self.display_image(Image.open(fpath))
            
            # Update menu states
            self.menu_refs['pattern_menu'].entryconfig('gen', state="normal")
            self.menu_refs['pattern_menu'].entryconfig('gen_nobg', state="normal")
            self.menu_refs['view_menu'].entryconfig('clear', state="normal")

    def display_image(self, pil_img):
        """Resizes and renders the image on the canvas."""
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
        """Runs the background removal and pattern generation logic."""
        if not self.input_path: return
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
                if not success and not mb.askyesno("AI", self.texts.get("msg_no_obj_text", "No objects found. Continue?")):
                    return

            self.current_pattern = el.generate_embroidery_pattern(
                img,
                self.settings['kmeans_n_clusters'].get(),
                self.settings['crosses_x'].get()
            )
            self.display_image(self.current_pattern['pil_image'])
            self.menu_refs['pattern_menu'].entryconfig('edit', state="normal")
            self.menu_refs['file_menu'].entryconfig('save', state="normal")
            
        except Exception as e:
            mb.showerror("Error", str(e))
        finally:
            self.master.config(cursor="")

    def handle_click(self, event, motion=False):
        """Maps canvas mouse coordinates to pattern grid coordinates."""
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
        """Modifies the grid and updates the view."""
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
            self.menu_refs['pattern_menu'].entryconfig('undo', state="normal")

        self.current_pattern = el.update_pattern_at_coord(pat, row, col, self.selected_color_idx)
        self.display_image(self.current_pattern['pil_image'])

    def undo(self, event=None):
        if self.history:
            self.current_pattern = self.history.pop()
            self.display_image(self.current_pattern['pil_image'])
            if not self.history:
                self.menu_refs['pattern_menu'].entryconfig('undo', state="disabled")

    def open_palette(self):
        """Creates a floating window for thread color selection."""
        if self.palette_window: self.palette_window.destroy()
        
        self.palette_window = tk.Toplevel(self)
        self.palette_window.title(self.texts.get("color_sel", "Colors"))
        self.palette_window.geometry("200x400")
        self.palette_window.attributes("-topmost", True)
        
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

        tk.Button(frame, text="Eraser", bg="white", command=lambda: select(255)).pack(fill="x")
        
        centers = self.current_pattern['cluster_centers']
        for i, color in enumerate(centers):
            hex_c = '#%02x%02x%02x' % tuple(color)
            fg = "white" if np.mean(color) < 128 else "black"
            tk.Button(frame, text=f"ID {i}", bg=hex_c, fg=fg, command=lambda idx=i: select(idx)).pack(fill="x")

        frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def change_zoom(self, delta, reset=False):
        self.zoom_level = 1.0 if reset else max(1.0, self.zoom_level + delta)
        img = self.current_pattern['pil_image'] if self.current_pattern else Image.open(self.input_path)
        self.display_image(img)

    def clear_all(self):
        self.canvas.delete("all")
        self.input_path = None
        self.current_pattern = None
        self.master.config(cursor="")
        # Reset menu states...

    def load_settings(self):
        # Implementation of JSON loading...
        pass

    def save_pattern(self):
        # PDF/JPEG export logic...
        pass

    def open_settings(self):
        # Settings window logic...
        pass

    def bind_shortcuts(self):
        self.master.bind("<Control-z>", self.undo)

