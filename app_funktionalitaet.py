# -*- coding: utf-8 -*-
"""
This file contains the description (class) of the graphical user interface of the Stick-App.

@author: thors
"""

import tkinter as tk
import tkinter.filedialog as fd
from tkinter import ttk
import tkinter.messagebox as mb
from os import path
from PIL import ImageTk, Image
import stick_funktionalitaet as sf

class StickApp(tk.Frame):
    """
    GUI application for generating and saving embroidery patterns.
    """

    def __init__(self, master):
        """
        Initializes the StickApp with a Menubar.
        """
        super().__init__(master)
        self.master = master
        self.pack(fill="both", expand=True)
        
        self.input_path = None
        self.current_pattern = None
        
        self.create_menubar()

        self.image_label = ttk.Label(self)
        self.image_label.pack(pady=20, padx=20, expand=True)

    def create_menubar(self):
        """
        Creates the top menu bar and its submenus.
        """
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # --- "Datei" Menu ---
        self.datei_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Datei", menu=self.datei_menu)
        
        self.datei_menu.add_command(label="Bild auswählen", command=self.load_image)
        # We save a reference to the 'Save' command to enable/disable it later
        self.datei_menu.add_command(label="Muster speichern", 
                                    command=self.save_pattern, 
                                    state="disabled")
        self.datei_menu.add_separator()
        self.datei_menu.add_command(label="Beenden", command=self.master.quit)

        # --- "Stickmuster" Menu ---
        self.stick_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Stickmuster", menu=self.stick_menu)
        
        self.stick_menu.add_command(label="Muster generieren", 
                                    command=lambda: self.process(False), 
                                    state="disabled")
        self.stick_menu.add_command(label="Muster (ohne Hintergrund)", 
                                    command=lambda: self.process(True), 
                                    state="disabled")

    def load_image(self):
        """
        Opens a file dialog to select a source image.
        """
        self.input_path = fd.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if self.input_path:
            self.display_image(Image.open(self.input_path))
            self.current_pattern = None
            
            # Enable pattern generation now that an image is loaded
            self.stick_menu.entryconfig("Muster generieren", state="normal")
            self.stick_menu.entryconfig("Muster (ohne Hintergrund)", state="normal")
            # Disable save until a new pattern is actually processed
            self.datei_menu.entryconfig("Muster speichern", state="disabled")

    def process(self, remove_bg):
        """
        Generates the embroidery pattern and updates the UI preview.
        """
        if not self.input_path:
            mb.showerror("Fehler", "Bitte zuerst ein Bild auswählen.")
            return

        img = Image.open(self.input_path)
        
        # Change cursor to 'watch' (hourglass) during processing
        self.master.config(cursor="watch")
        self.master.update()
        
        try:
            if remove_bg:
                img = sf.remove_background(img)
            
            self.current_pattern = sf.generate_embroidery_pattern(img)
            self.display_image(self.current_pattern['pil_image'])
            
            # Enable saving
            self.datei_menu.entryconfig("Muster speichern", state="normal")
            mb.showinfo("Fertig", "Stickmuster wurde generiert.")
        except Exception as e:
            mb.showerror("Fehler", f"Fehler bei der Verarbeitung: {e}")
        finally:
            self.master.config(cursor="")

    def save_pattern(self):
        """
        Opens a save dialog and exports the current pattern.
        """
        if not self.current_pattern:
            return

        base_name = path.basename(path.splitext(self.input_path)[0])
        output_path = fd.asksaveasfilename(
            initialfile=f"Stickmuster_{base_name}",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf"), ("JPEG Image", "*.jpg")]
        )

        if output_path:
            if output_path.lower().endswith('.pdf'):
                sf.save_as_pdf(output_path, self.current_pattern, f"Stickmuster: {base_name}")
            else:
                sf.save_as_jpeg(output_path, self.current_pattern)
            mb.showinfo("Erfolg", f"Datei gespeichert unter:\n{output_path}")

    def display_image(self, pil_img):
        """
        Resizes and displays a PIL image in the GUI label.
        """
        # Resize for preview while maintaining aspect ratio
        display_h = 600
        display_w = int(pil_img.width * (display_h / pil_img.height))
        
        # Limit width if it exceeds window bounds
        if display_w > 1000:
            display_w = 1000
            display_h = int(pil_img.height * (display_w / pil_img.width))

        img_resized = pil_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(img_resized)
        self.image_label.configure(image=photo)
        self.image_label.image = photo
