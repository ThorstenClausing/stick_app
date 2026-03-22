# -*- coding: utf-8 -*-
"""
Script to run the embroidery app.
"""

import tkinter as tk
from embroidery_gui import StickApp

def main():
    root = tk.Tk()
    root.title("Stick App")
    
    # Center window
    w, h = 1100, 850
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(ws-w)//2}+{(hs-h)//2}")

    app = StickApp(root)
    app.mainloop()

if __name__ == "__main__":
    main()