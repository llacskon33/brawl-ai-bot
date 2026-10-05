"""
Módulo de análisis táctico.
Evalúa la situación: amenaza, cobertura, línea de visión, etc.
"""

import math
import numpy as np
from config import CELL, ATTACK_RANGE, SAFE_DISTANCE, DANGER_DISTANCE, LOW_HP
from models import Situation
from memory import dist

def cell_of(pos):
    """Convierte coordenadas (x, y) a celda de rejilla (row, col)."""
    return int(pos[1] // CELL), int(pos[0] // CELL)

def line_blocked(walls, a, b):
    """Detecta si hay pared entre dos puntos (A y B)."""
    n = int(dist(a, b) // (CELL / 2)) + 1
    for i in range(1, n):
        t = i / n
        r, c = cell_of((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        if 0 <= r < walls.shape[0] and 0 <= c < walls.shape[1] and walls[r, c]:
            return True
    return False

def is_free(walls, pos):
    """Comprueba si una posición es libre de paredes."""
    r, c = cell_of(pos)
    return 0 <= r < walls.shape[0] and 0 <= c < walls.shape[1] and not walls[r, c]

def exposure(walls, pos, enemies):
    """
    Calcula exposición: fracción de enemigos con línea de visión a pos.
    0.0 = completamente escondido, 1.0 = completamente expuesto.
    """
    if not enemies:
        return 0.0
    return sum(not line_blocked(walls, e.pos, pos) for e in enemies) / len(enemies)

def incoming_projectiles(perc, player):
    """Detecta proyectiles que se acercan al jugador."""
    out = []
    for pr in perc.projectiles:
        vx, vy = pr.vel
        sp = math.hypot(vx, vy)
        if sp < 1:
            continue
        dx = player.pos[0] - pr.pos[0]
        dy = player.pos[1] - pr.pos[1]
        # Proyección en la dirección de movimiento del proyectil
        proj = (dx * vx + dy * vy) / sp
        if proj <= 0:  # Se aleja
            continue
        # Distancia perpendicular a la trayectoria
        perp = abs(dx * vy - dy * vx) / sp
        if perp < 40 and proj < 400:  # Cercano y potencialmente impactará
            out.append(pr)
    return out

def find_cover(perc, pos, enemies, radius=140):
    """
    Encuentra la mejor posición de cobertura cercana.
    Prefiere arbustos y posiciones no expuestas.
    """
    best, best_score = None, 1e9
    gh, gw = perc.walls.shape
    r0, c0 = cell_of(pos)
    rr = int(radius // CELL)
    
    for r in range(max(0, r0 - rr), min(gh, r0 + rr + 1)):
        for c in range(max(0, c0 - rr), min(gw, c0 + rr + 1)):
            if perc.walls[r, c]:
                continue
            cand = (c * CELL + CELL / 2, r * CELL + CELL / 2)
            
            # Debe estar cerca de pared o arbusto
            near_wall = perc.walls[max(0, r-1):r+2, max(0, c-1):c+2].any()
            bush = perc.bushes[r, c]
            if not (near_wall or bush):
                continue
            
            exp = exposure(perc.walls, cand, enemies)
            score = exp * 200 + dist(cand, pos) - (40 if bush else 0)
            
            if exp < 0.5 and score < best_score:
                best, best_score = cand, score
    
    return best

def analyze(perc, mem, now=None) -> Situation:
    """
    Analiza la situación táctica actual.
    Devuelve Situation con todas las métricas evaluadas.
    """
    s = Situation()
    p = perc.player
    if not p:
        return s
    
    enemies = list(mem.enemies.values())
    vis = mem.visible_enemies()
    
    # Detectar si enemigos están atacando
    for e in enemies:
        e.wall_between = line_blocked(perc.walls, p.pos, e.pos)
        e.attacking = (e.visible and not e.wall_between and 
                      dist(e.pos, p.pos) < ATTACK_RANGE and e.approaching)

    # Evaluaciones simples
    s.hp_low = p.hp < LOW_HP
    s.near_enemies = sum(dist(e.pos, p.pos) < SAFE_DISTANCE for e in vis)
    s.incoming = incoming_projectiles(perc, p)

    # Nivel de amenaza (0..1)
    threat = 0.0
    for e in vis:
        d = max(1, dist(e.pos, p.pos))
        t = max(0, 1 - d / (ATTACK_RANGE * 1.2))
        if e.wall_between:
            t *= 0.4
        if e.approaching:
            t *= 1.3
        threat += t * (0.5 + e.hp * 0.5)
    threat += 0.4 * len(s.incoming)
    threat += 0.3 * (1 - p.hp)
    s.threat = float(min(1.0, threat))
    
    # Peligro inmediato
    s.immediate_danger = (bool(s.incoming) or 
                          any(dist(e.pos, p.pos) < DANGER_DISTANCE and not e.wall_between 
                              for e in vis))

    # Rodeado: enemigos en >180° de cobertura
    if s.near_enemies >= 2:
        angs = sorted(math.atan2(e.pos[1] - p.pos[1], e.pos[0] - p.pos[0]) 
                     for e in vis if dist(e.pos, p.pos) < SAFE_DISTANCE * 1.4)
        if len(angs) >= 2:
            gaps = [(angs[(i + 1) % len(angs)] - angs[i]) % (2 * math.pi) 
                    for i in range(len(angs))]
            s.surrounded = max(gaps) < math.pi * 1.1
    
    s.stuck = mem.stuck_counter >= 3

    # Cobertura cercana disponible
    s.cover_nearby = find_cover(perc, p.pos, vis, radius=140) is not None

    # Mejor objetivo para atacar
    cands = [e for e in vis if dist(e.pos, p.pos) <= ATTACK_RANGE and not e.wall_between]
    if cands:
        s.best_target = min(cands, key=lambda e: (e.hp, dist(e.pos, p.pos)))
        s.can_shoot = True
    
    # Ventaja enemiga
    my_hp = p.hp
    s.enemy_advantage = ((s.near_enemies >= 2) or 
                         (vis and my_hp < min(e.hp for e in vis) - 0.25))
    
    return s
