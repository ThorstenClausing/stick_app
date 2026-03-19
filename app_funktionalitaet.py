# -*- coding: utf-8 -*-
"""
This file contains the description (class) of the graphical user interface of the Stick-App.

@author: Thorsten
"""

import tkinter as tk
import tkinter.filedialog as fd
from tkinter import ttk
import tkinter.messagebox as mb
from os import path
from PIL import ImageTk, Image
import stick_funktionalitaet as sf

class StickApp(tk.Frame):
    
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(fill="both", expand=True)
        
        self.input_path = None
        self.current_pattern = None
        self.edit_mode = tk.StringVar(value="none") # "none" or "erase"
        self.selected_color = [255, 255, 255] 

        self.settings = {
            "crosses_x": tk.IntVar(value=150),
            "kmeans_n_clusters": tk.IntVar(value=20),
            "score_threshold": tk.DoubleVar(value=0.75),
            "num_objects": tk.IntVar(value=1),
            "model_version": tk.StringVar(value="Version 1"),
            "paper_size": tk.StringVar(value="A4")
        }
        
        self.create_menubar()
        
        # Main Canvas area
        self.canvas = tk.Canvas(self, bg="gray70", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Events for editing
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_click)
        
    def create_menubar(self):
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # Datei Menu
        self.datei_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Datei", menu=self.datei_menu)
        self.datei_menu.add_command(label="Bild auswählen", command=self.load_image)
        self.datei_menu.add_command(label="Anzeige leeren", command=self.clear_display, state="disabled")        
        self.datei_menu.add_command(label="Muster speichern", command=self.save_pattern, state="disabled")
        self.datei_menu.add_separator()
        self.datei_menu.add_command(label="Beenden", command=self.master.destroy)

        # Stickmuster Menu
        self.stick_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Stickmuster", menu=self.stick_menu)
        self.stick_menu.add_command(label="Muster generieren", command=lambda: self.process(False), state="disabled")
        self.stick_menu.add_command(label="Muster (ohne Hintergrund)", command=lambda: self.process(True), state="disabled")
        self.stick_menu.add_command(label="Muster nachbearbeiten", command=self.enable_edit_mode, state="disabled")

        # Einstellungen Menu
        self.settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Einstellungen", menu=self.settings_menu)
        self.settings_menu.add_command(label="Parameter anpassen", command=self.open_settings)

    def clear_display(self):
        """
        Resets the canvas and the application state.
        """
        self.canvas.delete("all")
        self.input_path = None
        self.current_pattern = None
        self.edit_mode.set("none")
        self.master.config(cursor="")
        
        # Disable pattern-specific menus
        self.stick_menu.entryconfig("Muster generieren", state="disabled")
        self.stick_menu.entryconfig("Muster (ohne Hintergrund)", state="disabled")
        self.stick_menu.entryconfig("Muster nachbearbeiten", state="disabled")
        self.datei_menu.entryconfig("Muster speichern", state="disabled")
        self.datei_menu.entryconfig("Anzeige leeren", state="disabled")

    def enable_edit_mode(self):
        """
        Activates the deletion tool.
        """
        if self.current_pattern:
            self.edit_mode.set("erase")
            self.selected_color = [255, 255, 255]
            self.master.config(cursor="cross") # Feedback that editing is active
            mb.showinfo("Nachbearbeiten", "Löschmodus aktiviert. Klicken oder ziehen Sie auf das Muster, um Stiche zu entfernen.")

    def open_settings(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("Einstellungen")
        settings_win.geometry("300x450")
        settings_win.grab_set()

        container = ttk.Frame(settings_win, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Anzahl Kreuzstiche horizontal:").pack(anchor="w")
        ttk.Entry(container, textvariable=self.settings["crosses_x"]).pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="Anzahl Farben:").pack(anchor="w")
        ttk.Entry(container, textvariable=self.settings["kmeans_n_clusters"]).pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="KI-Modell Version:").pack(anchor="w")
        ttk.Combobox(container, textvariable=self.settings["model_version"],
                     values=["Version 1", "Version 2"], state="readonly").pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="KI-Schwellenwert (0.1 - 1.0):").pack(anchor="w")
        ttk.Entry(container, textvariable=self.settings["score_threshold"]).pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="Anzahl Vordergrundobjekte:").pack(anchor="w")
        ttk.Entry(container, textvariable=self.settings["num_objects"]).pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="PDF Papierformat:").pack(anchor="w")
        ttk.Combobox(container, textvariable=self.settings["paper_size"],
                     values=["A4", "A3"], state="readonly").pack(fill="x", pady=(0, 20))

        ttk.Button(container, text="Speichern", command=settings_win.destroy).pack()

    def on_canvas_click(self, event):
        # Only allow clicks if a pattern exists AND edit mode is 'erase'
        if not self.current_pattern or self.edit_mode.get() != "erase": 
            return
        
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        img_w, img_h = self.current_pattern['pil_image'].size
        
        display_h = 600
        display_w = int(img_w * (display_h / img_h))
        if display_w > 1000:
            display_w = 1000
            display_h = int(img_h * (display_w / img_w))
            
        offset_x = (c_width - display_w) / 2
        offset_y = (c_height - display_h) / 2
        
        if offset_x <= event.x <= offset_x + display_w and offset_y <= event.y <= offset_y + display_h:
            rel_x = (event.x - offset_x) / display_w
            rel_y = (event.y - offset_y) / display_h
            
            orig_x = rel_x * img_w
            orig_y = rel_y * img_h
            
            matrix = self.current_pattern['matrix']
            grid_h, grid_w = matrix.shape
            
            col = int(orig_x // (img_w / grid_w))
            row = int(orig_y // (img_h / grid_h))
            
            if 0 <= row < grid_h and 0 <= col < grid_w:
                self.modify_pattern(row, col)

    def modify_pattern(self, row, col):
        self.current_pattern = sf.update_pattern_at_coord(
            self.current_pattern, row, col, self.selected_color
        )
        self.display_image(self.current_pattern['pil_image'])

    def display_image(self, pil_img):
        display_h = 600
        display_w = int(pil_img.width * (display_h / pil_img.height))
        if display_w > 1000:
            display_w = 1000
            display_h = int(pil_img.height * (display_w / pil_img.width))
            
        img_resized = pil_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img_resized)
        
        self.canvas.delete("all")
        self.canvas.create_image(
            self.canvas.winfo_width() // 2, 
            self.canvas.winfo_height() // 2, 
            image=self.photo)

    def load_image(self):
        path_selected = fd.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if path_selected:
            self.input_path = path_selected
            self.display_image(Image.open(self.input_path))
            self.current_pattern = None
            self.edit_mode.set("none")
            self.master.config(cursor="")
            
            self.datei_menu.entryconfig("Anzeige leeren", state="normal")
            self.stick_menu.entryconfig("Muster generieren", state="normal")
            self.stick_menu.entryconfig("Muster (ohne Hintergrund)", state="normal")
            self.stick_menu.entryconfig("Muster nachbearbeiten", state="disabled")
            self.datei_menu.entryconfig("Muster speichern", state="disabled")

    def process(self, remove_bg):
        if not self.input_path: return
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
                    answer = mb.askyesno("Hintergrund", "Kein Objekt erkannt. Ohne KI-Schnitt fortfahren?")
                    if not answer: return 
                    self.master.config(cursor="watch")
                    self.master.update()

            self.current_pattern = sf.generate_embroidery_pattern(
                processed_img, 
                kmeans_n_clusters=self.settings["kmeans_n_clusters"].get(),
                crosses_x=self.settings["crosses_x"].get())
            
            self.display_image(self.current_pattern['pil_image'])
            
            # Enable pattern-related tools
            self.stick_menu.entryconfig("Muster nachbearbeiten", state="normal")
            self.datei_menu.entryconfig("Muster speichern", state="normal")
            
        except Exception as e:
            mb.showerror("Fehler", f"Fehler: {e}")
        finally:
            self.master.config(cursor="")

    def save_pattern(self):
        if not self.current_pattern: return
        base_name = path.basename(path.splitext(self.input_path)[0])
        output_path = fd.asksaveasfilename(
            initialfile=f"Stickmuster_{base_name}",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf"), ("JPEG Image", "*.jpg")]
        )

        if output_path:
            if output_path.lower().endswith('.pdf'):
                p_size = sf.A3 if self.settings["paper_size"].get() == "A3" else sf.A4
                sf.save_as_pdf(output_path, self.current_pattern, f"Stickmuster: {base_name}", pagesize=p_size)
            else:
                sf.save_as_jpeg(output_path, self.current_pattern)
            mb.showinfo("Erfolg", "Datei gespeichert.")