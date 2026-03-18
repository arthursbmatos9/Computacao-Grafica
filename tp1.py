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
        self.canvas.grid(row=0, column=0, columnspan=7)
        self.canvas.bind("<Button-1>", self.on_click)

        tk.Radiobutton(root, text="DDA", variable=self.mode, value="dda").grid(row=1, column=0)
        tk.Radiobutton(root, text="Bresenham Reta", variable=self.mode, value="bresenham_reta").grid(row=1, column=1)
        tk.Radiobutton(root, text="Bresenham Círculo", variable=self.mode, value="bresenham_circ").grid(row=1, column=2)

        tk.Button(root, text="Limpar", command=self.clear).grid(row=1, column=5)
        tk.Button(root, text="Sair", command=root.quit).grid(row=1, column=6)

        self.points = []
        # store original lines so we can re-evaluate clipping when window changes
        self.lines = []  # each item: (x1,y1,x2,y2,method) method in {'dda','bresenham_reta'}
        self.circles = []  # each item: (xc, yc, r)

        # click-to-define clipping window state
        self.define_clip = False
        self.clip_points = []
        self.clip_marker_ids = []
        self.define_btn = tk.Button(root, text="Definir Janela", command=self.toggle_define_clip)
        self.define_btn.grid(row=1, column=3)

        # Clipping window is defined by two clicks; no manual entry UI
        tk.Button(root, text="Reset Janela", command=self.reset_clip_window).grid(row=1, column=4)

    def clear(self):
        self.canvas.delete("all")
        self.points = []
        self.lines = []
        self.circles = []
        self.draw_clip_window()

    def on_click(self, event):
        px = int(event.x / PIXEL_SIZE)
        py = int(event.y / PIXEL_SIZE)
        if px < 0 or py < 0 or px >= WIDTH_PIXELS or py >= HEIGHT_PIXELS:
            return
        # If user is defining clipping window by clicks
        if self.define_clip:
            self.clip_points.append((px, py))
            # draw temporary marker
            x1 = px * PIXEL_SIZE
            y1 = py * PIXEL_SIZE
            x2 = x1 + PIXEL_SIZE
            y2 = y1 + PIXEL_SIZE
            mid = self.canvas.create_rectangle(x1, y1, x2, y2, fill="blue", outline="blue", tags="clip_marker")
            self.clip_marker_ids.append(mid)
            if len(self.clip_points) == 2:
                (x1p, y1p), (x2p, y2p) = self.clip_points
                xmin = min(x1p, x2p)
                ymin = min(y1p, y2p)
                xmax = max(x1p, x2p)
                ymax = max(y1p, y2p)
                # apply and draw window directly (no manual entries)
                global Xmin, Ymin, Xmax, Ymax, WINDOW_DEFINED
                Xmin, Ymin, Xmax, Ymax = xmin, ymin, xmax, ymax
                WINDOW_DEFINED = True
                self.redraw_all_lines()
                # cleanup
                for cid in self.clip_marker_ids:
                    self.canvas.delete(cid)
                self.clip_marker_ids = []
                self.clip_points = []
                self.define_clip = False
                self.define_btn.config(text="Definir Janela")
            return

        mode = self.mode.get()
        if mode in ("dda", "bresenham_reta"):
            self.points.append((px, py))
            # show a small marker while selecting
            self.draw_pixel(px, py)
            if len(self.points) == 2:
                (x1, y1), (x2, y2) = self.points
                # store the original line and redraw all lines with current clipping
                self.lines.append((x1, y1, x2, y2, mode))
                self.points = []
                self.redraw_all_lines()
        else:
            r = simpledialog.askinteger("Raio", "Digite o raio (em pixels):", parent=self.root, minvalue=1, maxvalue=1000)
            if r is None:
                return
            # store circle and redraw with clipping (circles handled like lines)
            self.circles.append((px, py, r))
            self.redraw_all_lines()

    def draw_pixel(self, x, y):
        color = "black"
        x1 = x * PIXEL_SIZE
        y1 = y * PIXEL_SIZE
        x2 = x1 + PIXEL_SIZE
        y2 = y1 + PIXEL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def draw_pixel_color(self, x, y, color):
        x1 = x * PIXEL_SIZE
        y1 = y * PIXEL_SIZE
        x2 = x1 + PIXEL_SIZE
        y2 = y1 + PIXEL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    # Window is applied via two-click 'Definir Janela'; no manual apply method

    def draw_clip_window(self):
        # remove previous visual rectangle
        self.canvas.delete("clip_window")
        if not WINDOW_DEFINED:
            return
        x1 = Xmin * PIXEL_SIZE
        y1 = Ymin * PIXEL_SIZE
        x2 = (Xmax + 1) * PIXEL_SIZE
        y2 = (Ymax + 1) * PIXEL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2, tags="clip_window")

    def reset_clip_window(self):
        global Xmin, Ymin, Xmax, Ymax
        Xmin, Ymin, Xmax, Ymax = 0, 0, WIDTH_PIXELS - 1, HEIGHT_PIXELS - 1
        # no manual UI values to update
        # unset window defined and redraw (no clipping)
        global WINDOW_DEFINED
        WINDOW_DEFINED = False
        self.redraw_all_lines()

    def toggle_define_clip(self):
        self.define_clip = not self.define_clip
        if self.define_clip:
            self.clip_points = []
            for cid in self.clip_marker_ids:
                self.canvas.delete(cid)
            self.clip_marker_ids = []
            self.define_btn.config(text="Cancelar Definir")
        else:
            for cid in self.clip_marker_ids:
                self.canvas.delete(cid)
            self.clip_marker_ids = []
            self.clip_points = []
            self.define_btn.config(text="Definir Janela")
    
    def redraw_all_lines(self):
        # clear drawing (markers and previous lines), keep clip window redrawn at end
        self.canvas.delete("all")
            # draw each original line by computing its pixel list once, then
            # color pixels inside window black and outside lightgray. This preserves
            # pixel positions independently of clipping-rounding differences.
        for (x1, y1, x2, y2, method) in self.lines:
            if method == 'dda':
                pixels = dda_pixels(x1, y1, x2, y2)
            else:
                pixels = bresenham_pixels(x1, y1, x2, y2)

            for (px, py) in pixels:
                if WINDOW_DEFINED:
                    if obtemCodigo(px, py) == 0:
                        self.draw_pixel_color(px, py, "black")
                    else:
                        self.draw_pixel_color(px, py, "lightgray")
                else:
                    self.draw_pixel_color(px, py, "black")

        # draw circles stored
        for (xc, yc, r) in self.circles:
            pixels = bresenham_circ_pixels(xc, yc, r)
            for (px, py) in pixels:
                if WINDOW_DEFINED:
                    if obtemCodigo(px, py) == 0:
                        self.draw_pixel_color(px, py, "black")
                    else:
                        self.draw_pixel_color(px, py, "lightgray")
                else:
                    self.draw_pixel_color(px, py, "black")

        # redraw clip window on top
        self.draw_clip_window()


def colore(x, y, canvas_obj):
    if 0 <= x < WIDTH_PIXELS and 0 <= y < HEIGHT_PIXELS:
        # default color black
        try:
            canvas_obj.draw_pixel(x, y)
        except TypeError:
            canvas_obj.draw_pixel(x, y)

def colore_color(x, y, canvas_obj, color):
    if 0 <= x < WIDTH_PIXELS and 0 <= y < HEIGHT_PIXELS:
        # use draw_pixel_color if available
        # if drawing the "outside" color (lightgray) and a window is defined,
        # skip painting pixels that are inside the window so the clipped (black)
        # drawing can overwrite them exactly without gaps caused by rounding.
        if color in ("lightgray", "gray", "silver") and WINDOW_DEFINED:
            if obtemCodigo(x, y) == 0:
                return

        if hasattr(canvas_obj, 'draw_pixel_color'):
            canvas_obj.draw_pixel_color(x, y, color)
        else:
            canvas_obj.draw_pixel(x, y)


### ALGORITMOS ###

def dda(xi, yi, xf, yf, canvas_obj, color="black"):
    x = xi
    y = yi
    dx = xf - xi
    dy = yf - yi
    if color == "black":
        colore(x, y, canvas_obj)
    else:
        colore_color(x, y, canvas_obj, color)

    passos = max(abs(dx), abs(dy))

    if passos == 0:
        return

    Xincr = dx/passos
    Yincr = dy/passos

    for i in range(passos):
        x += Xincr
        y += Yincr
        if color == "black":
            colore(round(x), round(y), canvas_obj)
        else:
            colore_color(round(x), round(y), canvas_obj, color)

def bresenham_reta(xi, yi, xf, yf, canvas_obj, color="black"):
    x = xi
    y = yi

    dx = abs(xf - xi)
    dy = abs(yf - yi)

    sx = 1 if xf > xi else -1
    sy = 1 if yf > yi else -1

    if color == "black":
        colore(x, y, canvas_obj)
    else:
        colore_color(x, y, canvas_obj, color)

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

            if color == "black":
                colore(x, y, canvas_obj)
            else:
                colore_color(x, y, canvas_obj, color)

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

            if color == "black":
                colore(x, y, canvas_obj)
            else:
                colore_color(x, y, canvas_obj, color)

def bresenham_circunferencia(xc, yc, r, canvas_obj, color="black"):
    x = 0
    y = r
    p = 3 - 2 * r
    if color == "black":
        simetricos(x, y, xc, yc, canvas_obj)
    else:
        simetricos_color(x, y, xc, yc, canvas_obj, color)
    while x < y:
        if p < 0:
            p += 4 * x + 6
        else:
            p += 4 * (x-y) + 10
            y -= 1
        x += 1
        if color == "black":
            simetricos(x, y, xc, yc, canvas_obj)
        else:
            simetricos_color(x, y, xc, yc, canvas_obj, color)

def dda_pixels(xi, yi, xf, yf):
    x = xi
    y = yi
    dx = xf - xi
    dy = yf - yi
    pixels = []

    passos = max(abs(dx), abs(dy))
    pixels.append((round(x), round(y)))

    if passos == 0:
        return pixels

    Xincr = dx/passos
    Yincr = dy/passos

    for i in range(passos):
        x += Xincr
        y += Yincr
        pixels.append((round(x), round(y)))

    return pixels

def bresenham_pixels(xi, yi, xf, yf):
    x = xi
    y = yi
    pixels = [(x, y)]

    dx = abs(xf - xi)
    dy = abs(yf - yi)

    sx = 1 if xf > xi else -1
    sy = 1 if yf > yi else -1

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

            pixels.append((x, y))

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

            pixels.append((x, y))

    return pixels

def bresenham_circ_pixels(xc, yc, r):
    x = 0
    y = r
    p = 3 - 2 * r
    pts = set()

    def add_sym(xp, yp):
        pts.add((xc + xp, yc + yp))
        pts.add((xc - xp, yc + yp))
        pts.add((xc + xp, yc - yp))
        pts.add((xc - xp, yc - yp))
        pts.add((xc + yp, yc + xp))
        pts.add((xc - yp, yc + xp))
        pts.add((xc + yp, yc - xp))
        pts.add((xc - yp, yc - xp))

    add_sym(x, y)
    while x < y:
        if p < 0:
            p += 4 * x + 6
        else:
            p += 4 * (x - y) + 10
            y -= 1
        x += 1
        add_sym(x, y)

    # return sorted list for deterministic ordering
    return sorted(pts)

def simetricos(a, b, xc, yc, canvas_obj):
    colore(a + xc, b + yc, canvas_obj)
    colore(-a + xc, b + yc, canvas_obj)
    colore(a + xc, -b + yc, canvas_obj)
    colore(-a + xc, -b + yc, canvas_obj)
    colore(b + xc, a + yc, canvas_obj)
    colore(-b + xc, a + yc, canvas_obj)
    colore(b + xc, -a + yc, canvas_obj)
    colore(-b + xc, -a + yc, canvas_obj)

def simetricos_color(a, b, xc, yc, canvas_obj, color):
    colore_color(a + xc, b + yc, canvas_obj, color)
    colore_color(-a + xc, b + yc, canvas_obj, color)
    colore_color(a + xc, -b + yc, canvas_obj, color)
    colore_color(-a + xc, -b + yc, canvas_obj, color)
    colore_color(b + xc, a + yc, canvas_obj, color)
    colore_color(-b + xc, a + yc, canvas_obj, color)
    colore_color(b + xc, -a + yc, canvas_obj, color)
    colore_color(-b + xc, -a + yc, canvas_obj, color)

# Clipping window (defaults to full canvas)
Xmin = 0
Ymin = 0
Xmax = WIDTH_PIXELS - 1
Ymax = HEIGHT_PIXELS - 1
# whether a clipping window is currently defined by the user
WINDOW_DEFINED = False

def obtemCodigo(x, y):
    # if no window defined, consider point inside
    if not WINDOW_DEFINED:
        return 0
    code = 0
    if x < Xmin:
        code |= 1  # esquerda
    elif x > Xmax:
        code |= 2  # direita
    if y < Ymin:
        code |= 4  # inferior
    elif y > Ymax:
        code |= 8  # superior
    return code

def verificaBit(code, pos):
    return 1 if (code & (1 << pos)) != 0 else 0

def desenha(xa, ya, xb, yb, canvas_obj):
    bresenham_reta(xa, ya, xb, yb, canvas_obj)

def cohen_sutherland(Xa, Ya, Xb, Yb):
    """Return clipped segment (xa,ya,xb,yb) inside window, or None if rejected."""
    # if no window defined, return the original segment
    if not WINDOW_DEFINED:
        return (Xa, Ya, Xb, Yb)

    aceite = False
    feito = False

    Xa_f = float(Xa)
    Ya_f = float(Ya)
    Xb_f = float(Xb)
    Yb_f = float(Yb)

    while not feito:
        codA = obtemCodigo(round(Xa_f), round(Ya_f))
        codB = obtemCodigo(round(Xb_f), round(Yb_f))

        if codA == 0 and codB == 0:
            aceite = True
            feito = True

        elif (codA & codB) != 0:
            feito = True

        else:
            codTemp = codA if codA != 0 else codB

            if verificaBit(codTemp, 0):  # esquerda
                Xint = Xmin
                if Xb_f != Xa_f:
                    Yint = Ya_f + (Yb_f - Ya_f) * (Xmin - Xa_f) / (Xb_f - Xa_f)
                else:
                    Yint = Ya_f

            elif verificaBit(codTemp, 1):  # direita
                Xint = Xmax
                if Xb_f != Xa_f:
                    Yint = Ya_f + (Yb_f - Ya_f) * (Xmax - Xa_f) / (Xb_f - Xa_f)
                else:
                    Yint = Ya_f

            elif verificaBit(codTemp, 2):  # inferior
                Yint = Ymin
                if Yb_f != Ya_f:
                    Xint = Xa_f + (Xb_f - Xa_f) * (Ymin - Ya_f) / (Yb_f - Ya_f)
                else:
                    Xint = Xa_f

            elif verificaBit(codTemp, 3):  # superior
                Yint = Ymax
                if Yb_f != Ya_f:
                    Xint = Xa_f + (Xb_f - Xa_f) * (Ymax - Ya_f) / (Yb_f - Ya_f)
                else:
                    Xint = Xa_f

            if codTemp == codA:
                Xa_f = float(Xint)
                Ya_f = float(Yint)
            else:
                Xb_f = float(Xint)
                Yb_f = float(Yint)

    if aceite:
        return (round(Xa_f), round(Ya_f), round(Xb_f), round(Yb_f))

    return None

def cohen_sutherland_draw(Xa, Ya, Xb, Yb, canvas_obj):
    clipped = cohen_sutherland(Xa, Ya, Xb, Yb)
    if clipped:
        xa, ya, xb, yb = clipped
        desenha(xa, ya, xb, yb, canvas_obj)

def main():
    root = tk.Tk()
    root.title("TP1 - Desenho de Retas e Círculos")
    pc = PixelCanvas(root)
    root.mainloop()

if __name__ == '__main__':
    main()