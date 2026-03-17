# Colore
def colore(int x, int y, color cor)
    # Função para colorir o pixel (x, y) com a cor

# DDA
def dda(int xi, int yi, int xf, int yf, color cor):
    x = xi, y = yi, dx = xf-xi, dy = yf-yi
    
    colore(x, y , cor)

    if abs(dx) > abs(dy):
        passos = abs(dx)
    else:
        passos = abs(dy)

    Xincr = dx/passos
    Yincr = dy/passos

    for i in range(passos):
        x += Xincr
        y += Yincr
        colore(round(x), round(y), cor)
    

# Bresenham Retas
def bresenham_reta(int xi, int yi, int xf, int yf, color cor):
    x = xi, y = yi

    colore(x, y, cor)

    dx = xf - xi
    dy = yf - yi
    p = 2*dy - dx
    c1 = 2*dy
    c2 = 2*(dy - dx)

    while x < xf:
        x += 1
        if p < 0:
            p += c1
        else:
            p += c2
            y += 1

        colore(x, y, cor)


# Bresenam Circunferencias
def bresenham_circunferencia(int xc, int yc, int r, color cor):
    x = 0, y = r, p = 3 - 2*r

    simetricos(x, y, xc, yc, cor)

    while x < y:
        if p < 0:
            p += 4*x + 6
        else:
            p += 4*(x-y) + 10
            y -= 1
        x += 1

    simetricos(x, y, xc, yc, cor)

def simetricos(int a, int b, int xc, int yc, color cor):
    colore(a + xc, b + yc, cor)
    colore(-a + xc, b + yc, cor)
    colore(a + xc, -b + yc, cor)
    colore(-a + xc, -b + yc, cor)
    colore(b + xc, a + yc, cor)
    colore(-b + xc, a + yc, cor)
    colore(b + xc, -a + yc, cor)
    colore(-b + xc, -a + yc, cor)