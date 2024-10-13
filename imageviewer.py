import tkinter as tk
import os
import pickle
from PIL import Image

imageDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\logs\\'

def buttonClick(filename, topPanel, bottomPanel):
    img = tk.PhotoImage(file=imageDir + filename + '.png')
    topPanel.config(image=img)
    topPanel.image = img

    with open(imageDir + filename + '.enc', 'rb') as f:
        faceEncoding = pickle.load(f)
    formattedEncoding = filename + '\n\n\n\n'
    for i in range(0, len(faceEncoding), 4):
        formattedEncoding += ' '.join(map(str, faceEncoding[i:i+4])) + '\n'
    bottomPanel.config(text=formattedEncoding, font=('Courier', 8))

window = tk.Tk()
window.title("imageviwer")
window.geometry("1000x700")
p1 = tk.PanedWindow(window)
p1.pack(fill=tk.BOTH, expand=1)
leftPanel = tk.Label(p1)
p1.add(leftPanel)
p2 = tk.PanedWindow(p1, orient=tk.VERTICAL)
p1.add(p2)
topPanel = tk.Label(p2, text="\n\n\n\n\n\n\n\n")
p2.add(topPanel)
bottomPanel = tk.Label(p2, text="\n\n\n\n\n\n\n\n")
p2.add(bottomPanel)

text = tk.Text(leftPanel, width=35)
text.pack(side="left")
sb = tk.Scrollbar(leftPanel, command=text.yview)
sb.pack(side="right", fill="y")
text.configure(yscrollcommand=sb.set)

for file in os.listdir(imageDir):
    if file.endswith('.enc'):
        filename = file.split('.')[0]
        button = tk.Button(text, text=f"{filename:35}", font=('Courier', 10), activebackground='darkgrey',
                           command=lambda filename=filename: buttonClick(filename, topPanel, bottomPanel))
        button.pack()
        text.window_create("end", window=button)
        text.insert("end", "\n")
text.configure(state="disabled")

window.mainloop()