import os
import tkinter as tk
from tkinter import filedialog


def openFile():
    filetypes = (
        ('SVG files', '*.svg'),
        ('All files', '*.*')
    )

    file_path = filedialog.askopenfilename(
            title='Open a SVG file',
            initialdir=os.getcwd(),
            filetypes=filetypes)
    
    return file_path

def getOutputFileName(filename):
    loop = 0
    outputFilename = filename.replace('.svg',f"_{loop}.gcode")
    
    while(os.path.isfile(outputFilename)):
        loop+=1
        outputFilename = filename.replace('.svg',f"_{loop}.gcode")

    return(outputFilename)

