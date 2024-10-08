import os
import tkinter as tk
# from tkinter import filedialog
from tkinter.filedialog import askopenfilename

def openFile(initialDir = os.getcwd()):
    filetypes = (
        ('Vector files', '*.svg *.dxf'),
        ('SVG files', '*.svg'),
        ('dxf files', '*.dxf'),
        ('All files', '*.*')
    )

    # file_path = filedialog.askopenfilename(
    file_path = askopenfilename(
            title='Open a SVG file',
            initialdir=initialDir,
            filetypes=filetypes)
    
    return file_path

def getOutputFileName(filename):
    loop = 0
    ext = ""
    if filename.__contains__(".svg"):
        outputFilename = filename.replace('.svg',f"_{loop}.gcode")
        ext = '.svg'
    elif filename.__contains__(".dxf"):
        outputFilename = filename.replace('.dxf',f"_{loop}.gcode")
        ext = '.dxf'
    else:
        return filename
    
    while(os.path.isfile(outputFilename)):
        loop+=1
        outputFilename = filename.replace(ext,f"_{loop}.gcode")

    return(outputFilename)

