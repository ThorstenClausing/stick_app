# -*- coding: utf-8 -*-
"""
This script starts the graphical user interface of the Stick-App.

Created on Sat Apr 27 18:34:16 2024

@author: Thorsten
"""

import tkinter as tk
from app_funktionalitaet import StickApp

def main():
    root = tk.Tk()
    root.title("Stick-App")

    window_width, window_height = 1100, 850 
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - window_width) // 2
    y = (screen_h - window_height) // 2 - 25
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    app = StickApp(root)
    app.mainloop()

if __name__ == "__main__":
    main()
