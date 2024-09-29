# -*- coding: utf-8 -*-
"""
This script starts the graphical user interface of the Stick-App.

Created on Sat Apr 27 18:34:16 2024

@author: Thorsten
"""

import tkinter as tk
from app_funktionalitaet import StickApp

def main():
    """
    Launches the main GUI application.

    This function creates the Tkinter root window, initializes the StickApp 
    GUI, sets the window size and position, and starts the main event loop.
    """
    root = tk.Tk()
    gui = StickApp(root)

    # Window dimensions and positioning
    window_width = 1100
    window_height = 800
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2 - 25
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    root.title("Stick-App")
    gui.mainloop()

if __name__ == "__main__":
    main()
