import tkinter as tk
from tkinter import simpledialog, messagebox
import math


# Interface gráfica e constantes do canvas
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
        self.canvas.grid(row=0, column=0, columnspan=10, sticky="ew")
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

        # UI: controles de desenho e clipping
        # Grupo: desenho
        draw_frame = tk.LabelFrame(root, text="Desenho", padx=4, pady=2)
        draw_frame.grid(row=1, column=0, columnspan=3, padx=4, pady=3, sticky="w")

        tk.Radiobutton(draw_frame, text="DDA",               variable=self.mode, value="dda").grid(row=0, column=0, padx=2)
        tk.Radiobutton(draw_frame, text="Bresenham Reta",    variable=self.mode, value="bresenham_reta").grid(row=0, column=1, padx=2)
        tk.Radiobutton(draw_frame, text="Bresenham Círculo", variable=self.mode, value="bresenham_circ").grid(row=0, column=2, padx=2)
        tk.Radiobutton(draw_frame, text="Bézier",            variable=self.mode, value="bezier").grid(row=0, column=3, padx=2)
        tk.Radiobutton(draw_frame, text="B-spline",          variable=self.mode, value="bspline").grid(row=0, column=4, padx=2)
        tk.Radiobutton(draw_frame, text="Selecionar",        variable=self.mode, value="selecionar").grid(row=0, column=5, padx=6)

        # Grupo: janela de clipping
        clip_win_frame = tk.LabelFrame(root, text="Janela de Clipping", padx=4, pady=2)
        clip_win_frame.grid(row=1, column=3, columnspan=2, padx=4, pady=3, sticky="w")

        self.define_btn = tk.Button(clip_win_frame, text="Definir", command=self.toggle_define_clip, width=7)
        self.define_btn.grid(row=0, column=0, padx=2)
        tk.Button(clip_win_frame, text="Reset", command=self.reset_clip_window, width=7).grid(row=0, column=1, padx=2)

        # Grupo: algoritmos de clipping
        clip_algo_frame = tk.LabelFrame(root, text="Algoritmo de Clipping", padx=4, pady=2)
        clip_algo_frame.grid(row=1, column=5, columnspan=3, padx=4, pady=3, sticky="w")

        self.clip_algo = tk.StringVar(value="cohen")
        tk.Radiobutton(clip_algo_frame, text="C. Sutherland", variable=self.clip_algo, value="cohen").grid(row=0, column=0, padx=2)
        tk.Radiobutton(clip_algo_frame, text="L. Barsky",     variable=self.clip_algo, value="liang").grid(row=0, column=1, padx=2)

        # Ações principais
        tk.Button(root, text="Limpar", command=self.clear,      width=8).grid(row=1, column=7, padx=4, pady=3)
        tk.Button(root, text="Sair",   command=root.quit,       width=8).grid(row=1, column=8, padx=4, pady=3)

        self.points = []
        # Linhas originais (para recalcular clipping)
        self.lines = []  # item: (x1,y1,x2,y2,method) method in {'dda','bresenham_reta'}
        self.circles = []  # item: (xc, yc, r)
        self.beziers = []  # item: (p0, p1, p2, p3) pontos de controle da cúbica
        self.bsplines = []  # item: (p0, p1, ..., pn) pontos de controle, n >= 3
        self.bspline_temp = []  # pontos da B-spline sendo coletados (clique direito finaliza)
        self.selected = None  # ('line', idx) | ('circle', idx) | ('bezier', idx) | ('bspline', idx) | None

        # Estado: definir janela por cliques
        self.define_clip = False
        self.clip_points = []
        self.clip_marker_ids = []

        # Transformações geométricas
        transf_frame = tk.LabelFrame(root, text="Transformações Geométricas", padx=4, pady=2)
        transf_frame.grid(row=2, column=0, columnspan=9, padx=4, pady=3, sticky="w")

        tk.Button(transf_frame, text="Translação",  command=self.aplicar_translacao,              width=10).grid(row=0, column=0, padx=3)
        tk.Button(transf_frame, text="Rotação",     command=self.aplicar_rotacao,                 width=10).grid(row=0, column=1, padx=3)
        tk.Button(transf_frame, text="Escala",      command=self.aplicar_escala,                  width=10).grid(row=0, column=2, padx=3)
        tk.Button(transf_frame, text="Reflexão X",  command=lambda: self.aplicar_reflexao('x'),  width=10).grid(row=0, column=3, padx=3)
        tk.Button(transf_frame, text="Reflexão Y",  command=lambda: self.aplicar_reflexao('y'),  width=10).grid(row=0, column=4, padx=3)
        tk.Button(transf_frame, text="Reflexão XY", command=lambda: self.aplicar_reflexao('xy'), width=10).grid(row=0, column=5, padx=3)

    # Utilitários

    def ask_float(self, titulo, prompt):
        """Pede um número ao usuário aceitando vírgula ou ponto decimal."""
        raw = simpledialog.askstring(titulo, prompt, parent=self.root)
        if raw is None:
            return None
        raw = raw.strip().replace(',', '.')
        try:
            return float(raw)
        except ValueError:
            messagebox.showerror("Erro", f"Valor inválido: '{raw}'", parent=self.root)
            return None

    # Transformações geométricas 2D

    # Verifica se há um objeto selecionado
    def _check_selected(self):
        if self.selected is None:
            messagebox.showwarning("Seleção",
                "Nenhum objeto selecionado.\nUse o modo Selecionar e clique num objeto.",
                parent=self.root)
            return False
        return True

    # Seleciona o objeto (reta ou círculo)
    def selecionar_objeto(self, px, py):
        LIMIAR = 5
        melhor_idx = None
        melhor_tipo = None
        melhor_dist = float('inf')

        for i, (x1, y1, x2, y2, _m) in enumerate(self.lines):
            d = dist_ponto_segmento(px, py, x1, y1, x2, y2)
            if d < melhor_dist:
                melhor_dist = d
                melhor_idx = i
                melhor_tipo = 'line'

        for i, (xc, yc, r) in enumerate(self.circles):
            d = abs(math.hypot(px - xc, py - yc) - r)
            if d < melhor_dist:
                melhor_dist = d
                melhor_idx = i
                melhor_tipo = 'circle'

        for i, (p0, p1, p2, p3) in enumerate(self.beziers):
            d = dist_ponto_bezier(px, py, p0, p1, p2, p3)
            if d < melhor_dist:
                melhor_dist = d
                melhor_idx = i
                melhor_tipo = 'bezier'

        for i, pontos in enumerate(self.bsplines):
            d = dist_ponto_bspline(px, py, pontos)
            if d < melhor_dist:
                melhor_dist = d
                melhor_idx = i
                melhor_tipo = 'bspline'

        if melhor_dist <= LIMIAR:
            self.selected = (melhor_tipo, melhor_idx)
        else:
            self.selected = None

        self.redraw_all_lines()

    def _centroide(self):
        """Retorna o centroide (cx, cy) do objeto selecionado."""
        tipo, idx = self.selected
        if tipo == 'line':
            x1, y1, x2, y2, _m = self.lines[idx]
            return ((x1 + x2) / 2, (y1 + y2) / 2)
        elif tipo == 'bezier':
            pontos = self.beziers[idx]
            cx = sum(p[0] for p in pontos) / len(pontos)
            cy = sum(p[1] for p in pontos) / len(pontos)
            return (cx, cy)
        elif tipo == 'bspline':
            pontos = self.bsplines[idx]
            cx = sum(p[0] for p in pontos) / len(pontos)
            cy = sum(p[1] for p in pontos) / len(pontos)
            return (cx, cy)
        else:
            xc, yc, _r = self.circles[idx]
            return (float(xc), float(yc))

    def aplicar_translacao(self):
        if not self._check_selected(): return
        tx = self.ask_float("Translação", "Deslocamento em X (tx):")
        if tx is None: return
        ty = self.ask_float("Translação", "Deslocamento em Y (ty):")
        if ty is None: return

        # Translação: soma direta aos pontos do objeto
        tipo, idx = self.selected
        if tipo == 'line':
            x1, y1, x2, y2, m = self.lines[idx]
            self.lines[idx] = (round(x1+tx), round(y1+ty), round(x2+tx), round(y2+ty), m)
        elif tipo == 'bezier':
            pontos = self.beziers[idx]
            self.beziers[idx] = tuple((round(x+tx), round(y+ty)) for (x, y) in pontos)
        elif tipo == 'bspline':
            pontos = self.bsplines[idx]
            self.bsplines[idx] = tuple((round(x+tx), round(y+ty)) for (x, y) in pontos)
        else:
            xc, yc, r = self.circles[idx]
            self.circles[idx] = (round(xc+tx), round(yc+ty), r)
        self.redraw_all_lines()

    def aplicar_rotacao(self):
        if not self._check_selected(): return
        ang = self.ask_float("Rotação", "Ângulo de rotação em graus (ex: 34,67):")
        if ang is None: return
        rad = math.radians(ang)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        cx, cy = self._centroide()

        def rot(x, y):
            # Rotaciona em torno do centroide
            dx = x - cx
            dy = y - cy
            return (round(cx + dx * cos_a - dy * sin_a),
                    round(cy + dx * sin_a + dy * cos_a))

        tipo, idx = self.selected
        if tipo == 'line':
            x1, y1, x2, y2, m = self.lines[idx]
            self.lines[idx] = (*rot(x1, y1), *rot(x2, y2), m)
        elif tipo == 'bezier':
            pontos = self.beziers[idx]
            self.beziers[idx] = tuple(rot(x, y) for (x, y) in pontos)
        elif tipo == 'bspline':
            pontos = self.bsplines[idx]
            self.bsplines[idx] = tuple(rot(x, y) for (x, y) in pontos)
        else:
            xc, yc, r = self.circles[idx]
            # círculo: só o centro rota em torno de si mesmo → permanece no lugar
            # (rotação de círculo em torno do próprio centro não move nada visualmente)
            self.circles[idx] = (round(cx), round(cy), r)
        self.redraw_all_lines()

    def aplicar_escala(self):
        if not self._check_selected(): return
        sx = self.ask_float("Escala", "Fator de escala em X (sx):")
        if sx is None: return
        sy = self.ask_float("Escala", "Fator de escala em Y (sy):")
        if sy is None: return
        cx, cy = self._centroide()

        def scale(x, y):
            # Escala em relação ao centroide
            dx = x - cx
            dy = y - cy
            return (round(cx + dx * sx), round(cy + dy * sy))

        tipo, idx = self.selected
        if tipo == 'line':
            x1, y1, x2, y2, m = self.lines[idx]
            self.lines[idx] = (*scale(x1, y1), *scale(x2, y2), m)
        elif tipo == 'bezier':
            pontos = self.beziers[idx]
            self.beziers[idx] = tuple(scale(x, y) for (x, y) in pontos)
        elif tipo == 'bspline':
            pontos = self.bsplines[idx]
            self.bsplines[idx] = tuple(scale(x, y) for (x, y) in pontos)
        else:
            xc, yc, r = self.circles[idx]
            self.circles[idx] = (round(xc), round(yc), round(r * max(abs(sx), abs(sy))))
        self.redraw_all_lines()

    def aplicar_reflexao(self, eixo):
        if not self._check_selected(): return
        # Centro do grid (origem para reflexão)
        cx = WIDTH_PIXELS / 2
        cy = HEIGHT_PIXELS / 2

        mx = -1 if eixo in ('y', 'xy') else 1
        my = -1 if eixo in ('x', 'xy') else 1

        def reflect(x, y):
            # Reflete ponto em relação ao centro do grid
            dx = x - cx
            dy = y - cy
            return (round(cx + dx * mx), round(cy + dy * my))

        tipo, idx = self.selected

        if tipo == 'line':
            x1, y1, x2, y2, m = self.lines[idx]
            self.lines[idx] = (*reflect(x1, y1), *reflect(x2, y2), m)
        elif tipo == 'bezier':
            pontos = self.beziers[idx]
            self.beziers[idx] = tuple(reflect(x, y) for (x, y) in pontos)
        elif tipo == 'bspline':
            pontos = self.bsplines[idx]
            self.bsplines[idx] = tuple(reflect(x, y) for (x, y) in pontos)
        else:
            xc, yc, r = self.circles[idx]
            rx, ry = reflect(xc, yc)
            self.circles[idx] = (rx, ry, r)

        self.redraw_all_lines()

    def clear(self):
        # Limpa canvas e estruturas de dados
        self.canvas.delete("all")
        self.points = []
        self.lines = []
        self.circles = []
        self.beziers = []
        self.bsplines = []
        self.bspline_temp = []
        self.draw_clip_window()

    def on_click(self, event):
        px = int(event.x / PIXEL_SIZE)
        py = int(event.y / PIXEL_SIZE)
        if px < 0 or py < 0 or px >= WIDTH_PIXELS or py >= HEIGHT_PIXELS:
            return
        # Converte clique em coordenadas de pixel e trata interações
        if self.define_clip:
            self.clip_points.append((px, py))
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
                # Define janela de clipping com os dois pontos
                global Xmin, Ymin, Xmax, Ymax, WINDOW_DEFINED
                Xmin, Ymin, Xmax, Ymax = xmin, ymin, xmax, ymax
                WINDOW_DEFINED = True
                self.redraw_all_lines()
                # Limpa marcadores temporários
                for cid in self.clip_marker_ids:
                    self.canvas.delete(cid)
                self.clip_marker_ids = []
                self.clip_points = []
                self.define_clip = False
                self.define_btn.config(text="Definir")
            return

        mode = self.mode.get()

        if mode == "selecionar":
            self.selecionar_objeto(px, py)
            return

        if mode in ("dda", "bresenham_reta"):
            self.points.append((px, py))
            # Marcador visual durante seleção
            self.draw_pixel(px, py)
            if len(self.points) == 2:
                (x1, y1), (x2, y2) = self.points
                # Armazena a linha original e redesenha considerando clipping
                self.lines.append((x1, y1, x2, y2, mode))
                self.points = []
                self.redraw_all_lines()
        elif mode == "bezier":
            # Coleta 4 cliques: P0, P1, P2, P3 (pontos de controle da cúbica)
            self.points.append((px, py))
            self.draw_pixel(px, py)
            if len(self.points) == 4:
                p0, p1, p2, p3 = self.points
                self.beziers.append((p0, p1, p2, p3))
                self.points = []
                self.redraw_all_lines()
        elif mode == "bspline":
            # Coleta pontos de controle; clique direito finaliza a curva (mínimo 4 pontos)
            self.bspline_temp.append((px, py))
            self.draw_pixel(px, py)
        else:
            r = simpledialog.askinteger("Raio", "Digite o raio (em pixels):", parent=self.root, minvalue=1, maxvalue=1000)
            if r is None:
                return
            # Armazena círculo e redesenha (tratado como linha para clipping)
            self.circles.append((px, py, r))
            self.redraw_all_lines()

    def on_right_click(self, event):
        # Finaliza a B-spline em construção, se houver pontos suficientes
        if self.mode.get() != "bspline":
            return
        if len(self.bspline_temp) < 4:
            messagebox.showwarning("B-spline",
                "São necessários pelo menos 4 pontos de controle.\n"
                f"Pontos coletados até agora: {len(self.bspline_temp)}.",
                parent=self.root)
            return
        self.bsplines.append(tuple(self.bspline_temp))
        self.bspline_temp = []
        self.redraw_all_lines()


    def draw_pixel(self, x, y):
        # Desenha um pixel escalado por PIXEL_SIZE
        color = "black"
        x1 = x * PIXEL_SIZE
        y1 = y * PIXEL_SIZE
        x2 = x1 + PIXEL_SIZE
        y2 = y1 + PIXEL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def draw_pixel_color(self, x, y, color):
        # Desenha pixel com cor específica
        x1 = x * PIXEL_SIZE
        y1 = y * PIXEL_SIZE
        x2 = x1 + PIXEL_SIZE
        y2 = y1 + PIXEL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    # Janela definida por dois cliques no canvas

    def draw_clip_window(self):
        # Remove retângulo anterior e desenha janela de clipping, se houver
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
        # Restaura janela para todo o canvas (desativa clipping)
        global WINDOW_DEFINED
        WINDOW_DEFINED = False
        self.redraw_all_lines()

    def toggle_define_clip(self):
        # Alterna modo de definição da janela por clique
        self.define_clip = not self.define_clip
        if self.define_clip:
            self.clip_points = []
            for cid in self.clip_marker_ids:
                self.canvas.delete(cid)
            self.clip_marker_ids = []
            self.define_btn.config(text="Cancelar")
        else:
            for cid in self.clip_marker_ids:
                self.canvas.delete(cid)
            self.clip_marker_ids = []
            self.clip_points = []
            self.define_btn.config(text="Definir")
    
    def redraw_all_lines(self):
        # Redesenha todas as primitivas aplicando clipping e seleção
        self.canvas.delete("all")
        # Para cada linha, calcula pixels e aplica política de cor
        for i, (x1, y1, x2, y2, method) in enumerate(self.lines):
            cor_dentro = "blue" if self.selected == ('line', i) else "black"

            if method == 'dda':
                pixels = dda_pixels(x1, y1, x2, y2)
            else:
                pixels = bresenham_pixels(x1, y1, x2, y2)

            if WINDOW_DEFINED:
                # Obtem segmento recortado pelo algoritmo selecionado
                if self.clip_algo.get() == "cohen":
                    clipped = cohen_sutherland(x1, y1, x2, y2)
                else:
                    clipped = liang_segment(x1, y1, x2, y2)

                clipped_pixels = set()
                if clipped:
                    cx1, cy1, cx2, cy2 = clipped
                    if method == 'dda':
                        clipped_pixels = set(dda_pixels(cx1, cy1, cx2, cy2))
                    else:
                        clipped_pixels = set(bresenham_pixels(cx1, cy1, cx2, cy2))

                for (px, py) in pixels:
                    if obtemCodigo(px, py) == 0:
                        self.draw_pixel_color(px, py, cor_dentro)
                    else:
                        self.draw_pixel_color(px, py, "lightgray")
            else:
                for (px, py) in pixels:
                    self.draw_pixel_color(px, py, cor_dentro)

        # Desenha círculos armazenados
        for i, (xc, yc, r) in enumerate(self.circles):
            cor_dentro = "blue" if self.selected == ('circle', i) else "black"

            pixels = bresenham_circ_pixels(xc, yc, r)
            for (px, py) in pixels:
                if WINDOW_DEFINED:
                    if obtemCodigo(px, py) == 0:
                        self.draw_pixel_color(px, py, cor_dentro)
                    else:
                        self.draw_pixel_color(px, py, "lightgray")
                else:
                    self.draw_pixel_color(px, py, cor_dentro)

        # Desenha curvas de Bézier armazenadas
        for i, (p0, p1, p2, p3) in enumerate(self.beziers):
            cor_dentro = "blue" if self.selected == ('bezier', i) else "black"

            # Polígono de controle, em cinza claro, como referência visual
            for (xa, ya), (xb, yb) in zip((p0, p1, p2), (p1, p2, p3)):
                for (px, py) in bresenham_pixels(xa, ya, xb, yb):
                    self.draw_pixel_color(px, py, "lightgray")

            pixels = bezier_pixels(p0, p1, p2, p3)
            for (px, py) in pixels:
                if WINDOW_DEFINED:
                    if obtemCodigo(px, py) == 0:
                        self.draw_pixel_color(px, py, cor_dentro)
                    else:
                        self.draw_pixel_color(px, py, "lightgray")
                else:
                    self.draw_pixel_color(px, py, cor_dentro)

        # Desenha B-splines armazenadas
        for i, pontos in enumerate(self.bsplines):
            cor_dentro = "blue" if self.selected == ('bspline', i) else "black"

            # Polígono de controle, em cinza claro, como referência visual
            for (xa, ya), (xb, yb) in zip(pontos, pontos[1:]):
                for (px, py) in bresenham_pixels(xa, ya, xb, yb):
                    self.draw_pixel_color(px, py, "lightgray")

            pixels = bspline_pixels(pontos)
            for (px, py) in pixels:
                if WINDOW_DEFINED:
                    if obtemCodigo(px, py) == 0:
                        self.draw_pixel_color(px, py, cor_dentro)
                    else:
                        self.draw_pixel_color(px, py, "lightgray")
                else:
                    self.draw_pixel_color(px, py, cor_dentro)

        # Redesenha janela de clipping sobre as primitivas
        self.draw_clip_window()


def colore(x, y, canvas_obj):
    if 0 <= x < WIDTH_PIXELS and 0 <= y < HEIGHT_PIXELS:
        try:
            canvas_obj.draw_pixel(x, y)
        except TypeError:
            canvas_obj.draw_pixel(x, y)
    # Desenha pixel sem cor explícita (wrapper)

def colore_color(x, y, canvas_obj, color):
    if 0 <= x < WIDTH_PIXELS and 0 <= y < HEIGHT_PIXELS:
        if color in ("lightgray", "gray", "silver") and WINDOW_DEFINED:
            if obtemCodigo(x, y) == 0:
                return

        if hasattr(canvas_obj, 'draw_pixel_color'):
            canvas_obj.draw_pixel_color(x, y, color)
        else:
            canvas_obj.draw_pixel(x, y)


# Algoritmos de rasterização

def dda(xi, yi, xf, yf, canvas_obj, color="black"):
    # DDA: desenha reta usando incremento uniforme
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

def dda_pixels(xi, yi, xf, yf):
    # DDA: retorna lista de pixels da reta
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

def bresenham_reta(xi, yi, xf, yf, canvas_obj, color="black"):
    # Bresenham (reta): desenha reta com decisões inteiras
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
    # Bresenham (circunferência): desenha círculos por simetria
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

def bresenham_pixels(xi, yi, xf, yf):
    # Bresenham: retorna lista de pixels para segmento
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
    # Bresenham: pixels para circunferência (conjunto de pontos)
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

def bezier_ponto(t, p0, p1, p2, p3):
    """Avalia a curva cúbica de Bézier no parâmetro t (0 <= t <= 1).

    B(t) = (1-t)^3*P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3*P3

    Esta é a mesma forma polinomial explícita que o OpenGL calcula
    internamente via glMap1f/glEvalCoord1f no exemplo de referência
    (https://www.geeksforgeeks.org/cpp/bezier-curves-in-opengl/).
    """
    x = ((1-t)**3)*p0[0] + 3*((1-t)**2)*t*p1[0] + 3*(1-t)*(t**2)*p2[0] + (t**3)*p3[0]
    y = ((1-t)**3)*p0[1] + 3*((1-t)**2)*t*p1[1] + 3*(1-t)*(t**2)*p2[1] + (t**3)*p3[1]
    return (x, y)

# Quantidade de subdivisões do parâmetro t, equivalente ao "i / 30.0"
# usado pelo glEvalCoord1f no exemplo de referência
NUM_PASSOS_BEZIER = 30

def bezier_pixels(p0, p1, p2, p3, passos=NUM_PASSOS_BEZIER):
    """Curva de Bézier cúbica definida por 4 pontos de controle.

    Amostra a curva em `passos` subdivisões de t e liga os pontos
    consecutivos com Bresenham, reproduzindo no canvas em pixels o
    GL_LINE_STRIP usado pelo glBegin(GL_LINE_STRIP) do exemplo OpenGL.
    """
    amostras = []
    for i in range(passos + 1):
        t = i / passos
        x, y = bezier_ponto(t, p0, p1, p2, p3)
        amostras.append((round(x), round(y)))

    pixels = [amostras[0]]
    for (xa, ya), (xb, yb) in zip(amostras, amostras[1:]):
        pixels.extend(bresenham_pixels(xa, ya, xb, yb))
    return pixels

def dist_ponto_bezier(px, py, p0, p1, p2, p3, passos=NUM_PASSOS_BEZIER):
    """Distância mínima de (px, py) até a curva, por amostragem em t."""
    melhor = float('inf')
    anterior = bezier_ponto(0, p0, p1, p2, p3)
    for i in range(1, passos + 1):
        t = i / passos
        atual = bezier_ponto(t, p0, p1, p2, p3)
        d = dist_ponto_segmento(px, py, anterior[0], anterior[1], atual[0], atual[1])
        if d < melhor:
            melhor = d
        anterior = atual
    return melhor

# B-spline cúbica uniforme com vetor de nós fechado (clamped)
#
# Mesma ideia do exemplo de referência (scipy.interpolate.BSpline(t, c, k),
# https://www.geeksforgeeks.org/data-analysis/b-splines-using-scipy/), onde a
# curva é S(x) = soma_j c_j * B_{j,k}(x): os pontos de controle (c_j) são
# ponderados por funções de base (B_{j,k}) determinadas por um vetor de nós
# (t). Aqui o vetor de nós é gerado automaticamente e fechado nas
# extremidades, então a curva passa pelo primeiro e pelo último ponto de
# controle, mas tem suporte LOCAL: mover um ponto do meio só afeta a região
# vizinha da curva, diferente da Bézier (onde mover qualquer ponto afeta a
# curva inteira).

def bspline_knots(n, p):
    """Vetor de nós uniforme e fechado para n+1 pontos de controle e grau p."""
    knots = [0] * (p + 1)
    knots += list(range(1, n - p + 1))
    knots += [n - p + 1] * (p + 1)
    return knots

def bspline_base(i, p, u, knots):
    """Função de base B_{i,p}(u) pela recursão de Cox-de Boor."""
    if p == 0:
        if knots[i] <= u < knots[i + 1]:
            return 1.0
        # Inclui a borda direita do último intervalo (u == nó máximo)
        if u == knots[-1] and knots[i] <= u <= knots[i + 1]:
            return 1.0
        return 0.0

    termo1 = 0.0
    den1 = knots[i + p] - knots[i]
    if den1 != 0:
        termo1 = (u - knots[i]) / den1 * bspline_base(i, p - 1, u, knots)

    termo2 = 0.0
    den2 = knots[i + p + 1] - knots[i + 1]
    if den2 != 0:
        termo2 = (knots[i + p + 1] - u) / den2 * bspline_base(i + 1, p - 1, u, knots)

    return termo1 + termo2

def bspline_ponto(u, pontos_controle, p, knots):
    """Avalia a curva no parâmetro u: soma dos pontos de controle ponderados
    pelas funções de base, igual à fórmula S(x) = soma c_j * B_j(x)."""
    x = 0.0
    y = 0.0
    for i, (xi, yi) in enumerate(pontos_controle):
        b = bspline_base(i, p, u, knots)
        x += b * xi
        y += b * yi
    return (x, y)

def bspline_pixels(pontos_controle, passos=None):
    """B-spline cúbica uniforme definida por N pontos de controle (N >= 4).

    Amostra a curva no domínio válido do vetor de nós e liga os pontos
    consecutivos com Bresenham, do mesmo jeito que bezier_pixels.
    """
    n = len(pontos_controle) - 1
    p = min(3, n)  # grau cúbico, reduzido se houver poucos pontos de controle
    knots = bspline_knots(n, p)
    u_min = knots[p]
    u_max = knots[n + 1]

    if passos is None:
        passos = max(NUM_PASSOS_BEZIER, 15 * n)

    amostras = []
    for i in range(passos + 1):
        u = u_min + (u_max - u_min) * i / passos
        x, y = bspline_ponto(u, pontos_controle, p, knots)
        amostras.append((round(x), round(y)))
    # Garante que o último ponto amostrado seja exatamente o último ponto de
    # controle (evita arredondamento na borda do último nó)
    amostras[-1] = (round(pontos_controle[-1][0]), round(pontos_controle[-1][1]))

    pixels = [amostras[0]]
    for (xa, ya), (xb, yb) in zip(amostras, amostras[1:]):
        pixels.extend(bresenham_pixels(xa, ya, xb, yb))
    return pixels

def dist_ponto_bspline(px, py, pontos_controle, passos=None):
    """Distância mínima de (px, py) até a curva, por amostragem em u."""
    n = len(pontos_controle) - 1
    p = min(3, n)
    knots = bspline_knots(n, p)
    u_min = knots[p]
    u_max = knots[n + 1]

    if passos is None:
        passos = max(NUM_PASSOS_BEZIER, 15 * n)

    melhor = float('inf')
    anterior = bspline_ponto(u_min, pontos_controle, p, knots)
    for i in range(1, passos + 1):
        u = u_min + (u_max - u_min) * i / passos
        atual = bspline_ponto(u, pontos_controle, p, knots)
        d = dist_ponto_segmento(px, py, anterior[0], anterior[1], atual[0], atual[1])
        if d < melhor:
            melhor = d
        anterior = atual
    return melhor

def simetricos(a, b, xc, yc, canvas_obj):
    # Plota as 8 simetrias do ponto para circunferência
    colore(a + xc, b + yc, canvas_obj)
    colore(-a + xc, b + yc, canvas_obj)
    colore(a + xc, -b + yc, canvas_obj)
    colore(-a + xc, -b + yc, canvas_obj)
    colore(b + xc, a + yc, canvas_obj)
    colore(-b + xc, a + yc, canvas_obj)
    colore(b + xc, -a + yc, canvas_obj)
    colore(-b + xc, -a + yc, canvas_obj)

def simetricos_color(a, b, xc, yc, canvas_obj, color):
    # Versão colorida dos pontos simétricos
    colore_color(a + xc, b + yc, canvas_obj, color)
    colore_color(-a + xc, b + yc, canvas_obj, color)
    colore_color(a + xc, -b + yc, canvas_obj, color)
    colore_color(-a + xc, -b + yc, canvas_obj, color)
    colore_color(b + xc, a + yc, canvas_obj, color)
    colore_color(-b + xc, a + yc, canvas_obj, color)
    colore_color(b + xc, -a + yc, canvas_obj, color)
    colore_color(-b + xc, -a + yc, canvas_obj, color)

# Janela de clipping (padrão: todo o canvas)
Xmin = 0
Ymin = 0
Xmax = WIDTH_PIXELS - 1
Ymax = HEIGHT_PIXELS - 1
# Flag: janela definida pelo usuário
WINDOW_DEFINED = False

def obtemCodigo(x, y):
    # Retorna código de região (Cohen-Sutherland). 0 => dentro
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
    # Testa bit do código na posição pos
    return 1 if (code & (1 << pos)) != 0 else 0

def desenha(xa, ya, xb, yb, canvas_obj):
    # Wrapper que desenha reta com Bresenham
    bresenham_reta(xa, ya, xb, yb, canvas_obj)

def cohen_sutherland(Xa, Ya, Xb, Yb):
    """Return clipped segment (xa,ya,xb,yb) inside window, or None if rejected."""
    # Se sem janela, retorna segmento original
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
    # Desenha segmento recortado usando Cohen-Sutherland
    clipped = cohen_sutherland(Xa, Ya, Xb, Yb)
    if clipped:
        xa, ya, xb, yb = clipped
        desenha(xa, ya, xb, yb, canvas_obj)


def cliptTest(p, q, u1, u2):
    # Auxiliar Liang-Barsky: atualiza u1,u2 conforme p,q
    result = True
    if p < 0:
        r = q / p
        if r > u2:
            result = False
        elif r > u1:
            u1 = r
    elif p > 0:
        r = q / p
        if r < u1:
            result = False
        elif r < u2:
            u2 = r
    elif q < 0:
        result = False

    return result, u1, u2

def liang_segment(x1, y1, x2, y2):
    """Return clipped segment (x1,y1,x2,y2) inside window, or None if rejected."""
    if not WINDOW_DEFINED:
        return (x1, y1, x2, y2)

    u1 = 0.0
    u2 = 1.0
    dx = x2 - x1
    dy = y2 - y1

    result, u1, u2 = cliptTest(-dx, x1 - Xmin, u1, u2)
    if result:
        result, u1, u2 = cliptTest(dx, Xmax - x1, u1, u2)
        if result:
            result, u1, u2 = cliptTest(-dy, y1 - Ymin, u1, u2)
            if result:
                result, u1, u2 = cliptTest(dy, Ymax - y1, u1, u2)
                if result:
                    if u2 < 1:
                        x2 = x1 + u2 * dx
                        y2 = y1 + u2 * dy
                    if u1 > 0:
                        x1 = x1 + u1 * dx
                        y1 = y1 + u1 * dy
                    return (round(x1), round(y1), round(x2), round(y2))
    return None

def liang(x1, y1, x2, y2, canvas_obj):
    """Draw segment clipped by Liang-Barsky."""
    clipped = liang_segment(x1, y1, x2, y2)
    if clipped:
        cx1, cy1, cx2, cy2 = clipped
        desenha(cx1, cy1, cx2, cy2, canvas_obj)

def dist_ponto_segmento(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

def main():
    root = tk.Tk()
    root.title("TP1 - Desenho de Retas e Círculos")
    pc = PixelCanvas(root)
    root.mainloop()

if __name__ == '__main__':
    main()