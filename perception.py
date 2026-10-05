"""
Módulo de percepción visual (Apartado 1).
Analiza la imagen y extrae entidades, mapas de paredes y arbustos.
"""

import cv2
import numpy as np
from config import HSV, MIN_AREA, CELL
from models import Entity, Perception

def _mask(hsv, name):
    """Crea máscara binaria para un rango HSV."""
    lo, hi = HSV[name]
    return cv2.inRange(hsv, np.array(lo), np.array(hi))

def _blobs(mask):
    """Detecta blobs (entidades) en una máscara y devuelve centros y estadísticas."""
    n, _, stats, cent = cv2.connectedComponentsWithStats(mask)
    return [(tuple(cent[i]), stats[i]) for i in range(1, n)
            if stats[i][cv2.CC_STAT_AREA] >= MIN_AREA]

def _hp_bar(img, x, y, w):
    """
    Estima la vida leyendo una barra verde sobre la entidad.
    Extrae la zona superior de la entidad y mide qué fracción es verde.
    """
    y0 = max(0, int(y) - 14)
    strip = img[y0:y0 + 6, max(0, int(x - w)):int(x + w)]
    if strip.size == 0:
        return 1.0
    hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (40, 100, 100), (80, 255, 255)).any(axis=0).sum()
    total = max(1, strip.shape[1])
    return float(min(1.0, green / total)) if green else 1.0

def _grid(mask):
    """
    Convierte máscara binaria a rejilla de celdas (CELL x CELL píxeles).
    Devuelve np.ndarray bool donde True = bloqueado (pared/obstáculo).
    """
    h, w = mask.shape
    gh, gw = h // CELL, w // CELL
    m = mask[:gh * CELL, :gw * CELL].reshape(gh, CELL, gw, CELL).mean(axis=(1, 3))
    return m > 80

def perceive(img_bgr) -> Perception:
    """
    Analiza una imagen y extrae todas las entidades y mapas.
    
    Args:
        img_bgr: imagen en formato BGR (OpenCV)
    
    Returns:
        Perception: objeto con jugador, enemigos, proyectiles, objetivos y mapas
    """
    h, w = img_bgr.shape[:2]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Detectar jugador (blob más grande en azul)
    players = _blobs(_mask(hsv, "player"))
    player = None
    if players:
        (x, y), st = max(players, key=lambda b: b[1][cv2.CC_STAT_AREA])
        player = Entity(pos=(x, y), hp=_hp_bar(img_bgr, x, y, st[2] / 2))

    # Detectar enemigos (rojo)
    enemies = [Entity(pos=(x, y), hp=_hp_bar(img_bgr, x, y, st[2] / 2))
               for (x, y), st in _blobs(_mask(hsv, "enemy"))]
    
    # Detectar proyectiles (amarillo)
    projs = [Entity(pos=c) for c, _ in _blobs(_mask(hsv, "proj"))]
    
    # Detectar objetivos (magenta)
    goals = [c for c, _ in _blobs(_mask(hsv, "goal"))]

    return Perception((w, h), player, enemies, projs, goals,
                      _grid(_mask(hsv, "wall")), _grid(_mask(hsv, "bush")))
