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
        self.edit_mode = tk.StringVar(value="none") # "none", "draw", "erase"
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
        
        # UI Layout
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(side="top", fill="x", padx=5, pady=5)
        
        self.erase_btn = ttk.Button(self.toolbar, text="Radiergummi (Weiß)", command=self.set_eraser)
        self.erase_btn.pack(side="left", padx=5)
        
        ttk.Label(self.toolbar, text="Status:").pack(side="left", padx=(20, 5))
        self.status_label = ttk.Label(self.toolbar, text="Bereit")
        self.status_label.pack(side="left")

        # Use Canvas instead of Label for better coordinate control
        self.canvas = tk.Canvas(self, bg="gray70", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=20, pady=20)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_click) # Allow dragging

    def set_eraser(self):
        self.edit_mode.set("erase")
        self.selected_color = [255, 255, 255]
        self.status_label.config(text="Modus: Radieren (Klick ins Bild)")

    def on_canvas_click(self, event):
        if not self.current_pattern: return
        
        # 1. Get image display dimensions
        # We need to know where the image is inside the canvas
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        
        img_w, img_h = self.current_pattern['pil_image'].size
        
        # Calculate scaling used in display_image
        display_h = 600
        display_w = int(img_w * (display_h / img_h))
        if display_w > 1000:
            display_w = 1000
            display_h = int(img_h * (display_w / img_w))
            
        # Image offset in canvas (centered)
        offset_x = (c_width - display_w) / 2
        offset_y = (c_height - display_h) / 2
        
        # Check if click is inside image
        if offset_x <= event.x <= offset_x + display_w and offset_y <= event.y <= offset_y + display_h:
            # Map click to original PIL image coordinates
            rel_x = (event.x - offset_x) / display_w
            rel_y = (event.y - offset_y) / display_h
            
            orig_x = rel_x * img_w
            orig_y = rel_y * img_h
            
            # Map original coordinates to grid matrix
            matrix = self.current_pattern['matrix']
            grid_h, grid_w = matrix.shape
            
            col = int(orig_x // (img_w / grid_w))
            row = int(orig_y // (img_h / grid_h))
            
            # Bounds check
            if 0 <= row < grid_h and 0 <= col < grid_w:
                self.modify_pattern(row, col)

    def modify_pattern(self, row, col):
        # Update the data
        self.current_pattern = sf.update_pattern_at_coord(
            self.current_pattern, row, col, self.selected_color
        )
        
        # If we erased, we should also update the matrix index to something that
        # indicates "white" or "background" for the PDF export.
        # For now, we simply update the display.
        self.display_image(self.current_pattern['pil_image'])

    def display_image(self, pil_img):
        display_h = 600
        display_w = int(pil_img.width * (display_h / pil_img.height))
        if display_w > 1000:
            display_w = 1000
            display_h = int(pil_img.height * (display_w / pil_img.width))
            
        img_resized = pil_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img_resized)
        
        # Clear canvas and draw new image
        self.canvas.delete("all")
        self.canvas.create_image(
            self.canvas.winfo_width() // 2, 
            self.canvas.winfo_height() // 2, 
            image=self.photo)

    def load_image(self):
        self.input_path = fd.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if self.input_path:
            self.display_image(Image.open(self.input_path))
            self.current_pattern = None
            self.stick_menu.entryconfig("Muster generieren", state="normal")
            self.stick_menu.entryconfig("Muster (ohne Hintergrund)", state="normal")
            self.datei_menu.entryconfig("Muster speichern", state="disabled")

    def process(self, remove_bg):
        if not self.input_path: return
        img = Image.open(self.input_path)
        self.master.config(cursor="watch")
        self.master.update()
        
        try:
            processed_img = img
            
            if remove_bg:
                # Get the image and the success flag from the modified function
                processed_img, success = sf.remove_background(
                    img, 
                    score_threshold=self.settings["score_threshold"].get(),
                    num_objects=self.settings["num_objects"].get(),
                    model_version=self.settings["model_version"].get())
                
                # If removal failed, ask the user what to do
                if not success:
                    self.master.config(cursor="") # Reset cursor so user can click dialog
                    answer = mb.askyesno(
                        "Hintergrund nicht gefunden", 
                        "Es konnten keine Vordergrundobjekte erkannt werden. "
                        "Möchten Sie das Stickmuster stattdessen ohne Hintergrundentfernung erstellen?"
                    )
                    if not answer:
                        # User clicked 'No', stop processing
                        return 
                    # If 'Yes', processed_img remains the original 'img'
                    self.master.config(cursor="watch")
                    self.master.update()

            # Generate pattern from either the masked image or the original
            self.current_pattern = sf.generate_embroidery_pattern(
                processed_img, 
                kmeans_n_clusters=self.settings["kmeans_n_clusters"].get(),
                crosses_x=self.settings["crosses_x"].get())
            
            self.display_image(self.current_pattern['pil_image'])
            self.datei_menu.entryconfig("Muster speichern", state="normal")
            
        except Exception as e:
            mb.showerror("Fehler", f"Verarbeitungsfehler: {e}")
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
                # Map string selection to reportlab object
                p_size = sf.A3 if self.settings["paper_size"].get() == "A3" else sf.A4
                sf.save_as_pdf(output_path, self.current_pattern, f"Stickmuster: {base_name}", pagesize=p_size)
            else:
                sf.save_as_jpeg(output_path, self.current_pattern)
            mb.showinfo("Erfolg", "Datei gespeichert.")

    def display_image(self, pil_img):
        display_h = 600
        display_w = int(pil_img.width * (display_h / pil_img.height))
        if display_w > 1000:
            display_w = 1000
            display_h = int(pil_img.height * (display_w / pil_img.width))
        img_resized = pil_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img_resized)
        self.image_label.configure(image=photo)
        self.image_label.image = photo
