import tkinter as tk
from tkinter import simpledialog, messagebox
import math


## INTERFACE ## 

PIXEL_SIZE = 5
WIDTH_PIXELS = 256
HEIGHT_PIXELS = 150
CANVAS_WIDTH = PIXEL_SIZE * WIDTH_PIXELS
CANVAS_HEIGHT = PIXEL_SIZE * HEIGHT_PIXELS

class PixelCanvas:
    def __init__(self, root):
        self.root = root
        self.mode = tk.StringVar(value="dda")

        self.canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white")
        self.canvas.grid(row=0, column=0, columnspan=6)
        self.canvas.bind("<Button-1>", self.on_click)

        tk.Radiobutton(root, text="DDA", variable=self.mode, value="dda").grid(row=1, column=0)
        tk.Radiobutton(root, text="Bresenham Reta", variable=self.mode, value="bresenham_reta").grid(row=1, column=1)
        tk.Radiobutton(root, text="Bresenham Círculo", variable=self.mode, value="bresenham_circ").grid(row=1, column=2)

        tk.Button(root, text="Limpar", command=self.clear).grid(row=1, column=4)
        tk.Button(root, text="Sair", command=root.quit).grid(row=1, column=5)

        self.points = []

    def clear(self):
        self.canvas.delete("all")
        self.points = []

    def on_click(self, event):
        px = int(event.x / PIXEL_SIZE)
        py = int(event.y / PIXEL_SIZE)
        if px < 0 or py < 0 or px >= WIDTH_PIXELS or py >= HEIGHT_PIXELS:
            return

        mode = self.mode.get()
        if mode in ("dda", "bresenham_reta"):
            self.points.append((px, py))
            self.draw_pixel(px, py)
            if len(self.points) == 2:
                (x1, y1), (x2, y2) = self.points
                if mode == "dda":
                    dda(x1, y1, x2, y2, self)
                else:
                    bresenham_reta(x1, y1, x2, y2, self)
                self.points = []
        else:
            r = simpledialog.askinteger("Raio", "Digite o raio (em pixels):", parent=self.root, minvalue=1, maxvalue=1000)
            if r is None:
                return
            bresenham_circunferencia(px, py, r, self)

    def draw_pixel(self, x, y):
        color = "black"
        x1 = x * PIXEL_SIZE
        y1 = y * PIXEL_SIZE
        x2 = x1 + PIXEL_SIZE
        y2 = y1 + PIXEL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)


def colore(x, y, canvas_obj):
    if 0 <= x < WIDTH_PIXELS and 0 <= y < HEIGHT_PIXELS:
        canvas_obj.draw_pixel(x, y)


### ALGORITMOS ###

def dda(xi, yi, xf, yf, canvas_obj):
    x = xi
    y = yi
    dx = xf - xi
    dy = yf - yi
    colore(x, y, canvas_obj)

    passos = max(abs(dx), abs(dy))

    if passos == 0:
        return

    Xincr = dx/passos
    Yincr = dy/passos

    for i in range(passos):
        x += Xincr
        y += Yincr
        colore(round(x), round(y), canvas_obj)


def bresenham_reta(xi, yi, xf, yf, canvas_obj):
    x = xi
    y = yi

    dx = abs(xf - xi)
    dy = abs(yf - yi)

    sx = 1 if xf > xi else -1
    sy = 1 if yf > yi else -1

    colore(x, y, canvas_obj)

    if dx > dy:
        p = 2*dy - dx
        c1 = 2*dy
        c2 = 2*(dy - dx)

        while x != xf:
            x += sx

            if p < 0:
                p += c1
            else:
                p += c2
                y += sy

            colore(x, y, canvas_obj)

    else:
        p = 2*dx - dy
        c1 = 2*dx
        c2 = 2*(dx - dy)

        while y != yf:
            y += sy

            if p < 0:
                p += c1
            else:
                p += c2
                x += sx

            colore(x, y, canvas_obj)


def bresenham_circunferencia(xc, yc, r, canvas_obj):
    x = 0
    y = r
    p = 3 - 2 * r
    simetricos(x, y, xc, yc, canvas_obj)
    while x < y:
        if p < 0:
            p += 4 * x + 6
        else:
            p += 4 * (x-y) + 10
            y -= 1
        x += 1
        simetricos(x, y, xc, yc, canvas_obj)

def simetricos(a, b, xc, yc, canvas_obj):
    colore(a + xc, b + yc, canvas_obj)
    colore(-a + xc, b + yc, canvas_obj)
    colore(a + xc, -b + yc, canvas_obj)
    colore(-a + xc, -b + yc, canvas_obj)
    colore(b + xc, a + yc, canvas_obj)
    colore(-b + xc, a + yc, canvas_obj)
    colore(b + xc, -a + yc, canvas_obj)
    colore(-b + xc, -a + yc, canvas_obj)

def main():
    root = tk.Tk()
    root.title("TP1 - Desenho de Retas e Círculos")
    pc = PixelCanvas(root)
    root.mainloop()

if __name__ == '__main__':
    main()