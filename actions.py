"""
Módulo de generación de acciones (Apartados 2, 4, 5, 6, 7).
Genera acciones candidatas con puntuación según el estado.
"""

import math
import random
from config import CELL, ATTACK_RANGE, SAFE_DISTANCE, NOISE
from models import Action
from memory import dist
from analysis import find_cover, exposure, is_free

# 8 direcciones cardinales + diagonales
DIRS = [(math.cos(a * math.pi / 4), math.sin(a * math.pi / 4)) for a in range(8)]

def _norm(v):
    """Normaliza un vector."""
    n = math.hypot(*v) or 1
    return (v[0] / n, v[1] / n)

def _add_noise(d):
    """Añade variación aleatoria a una dirección."""
    angle = math.atan2(d[1], d[0]) + random.uniform(-NOISE, NOISE)
    return (math.cos(angle), math.sin(angle))

def generate(perc, mem, sit, state):
    """
    Genera acciones candidatas según el estado actual.
    Cada acción tiene un score basado en características tácticas.
    
    Args:
        perc: Perception actual
        mem: Memory del bot
        sit: Situation evaluada
        state: Estado actual de la máquina
    
    Returns:
        lista de Action ordenadas por score (descendente)
    """
    p = perc.player
    if not p:
        return []
    
    vis = mem.visible_enemies()
    known = list(mem.enemies.values())
    cands = []
    step = CELL * 3

    # ========== ACCIONES DE MOVIMIENTO ==========
    for d in DIRS:
        dest = (p.pos[0] + d[0] * step, p.pos[1] + d[1] * step)
        if not is_free(perc.walls, dest):
            continue
        
        action = Action(kind="MOVE", direction=d, label=f"Move {d}")
        feat = {}
        
        # Seguridad: cuántos enemigos ven esta posición
        feat["safety"] = 1 - exposure(perc.walls, dest, vis)
        
        # Distancia a enemigos
        if known:
            nearest = min(known, key=lambda e: dist(e.pos, dest))
            dn = dist(nearest.pos, dest)
            feat["away"] = min(1, dn / ATTACK_RANGE)
            feat["range"] = 1 - min(1, abs(dn - SAFE_DISTANCE * 1.3) / ATTACK_RANGE)
        else:
            feat["away"] = 0.5
            feat["range"] = 0.0
        
        # Progreso hacia objetivo
        feat["goal"] = 0.0
        if perc.goals:
            g = min(perc.goals, key=lambda g: dist(g, p.pos))
            feat["goal"] = max(0, min(1, (dist(g, p.pos) - dist(g, dest)) / step))
        
        # Esquivar proyectiles
        feat["dodge"] = 0.0
        for pr in sit.incoming:
            vx, vy = _norm(pr.vel)
            perp = (-vy, vx)
            feat["dodge"] = max(feat["dodge"], abs(d[0] * perp[0] + d[1] * perp[1]))
        
        # Estar cerca de cobertura
        cover = find_cover(perc, dest, vis)
        feat["cover"] = 1.0 if cover and dist(cover, dest) < 40 else 0.0
        
        # Espacio abierto (para no quedarse atrapado)
        adjacent_free = sum(
            1 for d2 in DIRS if is_free(perc.walls, (dest[0] + d2[0]*CELL, dest[1] + d2[1]*CELL))
        )
        feat["wall_dist"] = adjacent_free / 8.0
        
        # Evitar zonas peligrosas conocidas
        feat["danger_zone"] = max([
            1 - min(1, dist(dest, z) / 100) for z, _ in mem.danger_zones
        ], default=0.0)
        
        # Calcular score según estado
        score = _score_action(state, feat, sit, p, dest, perc)
        action.score = score
        cands.append(action)

    # ========== ACCIÓN DE ESPERA (HOLD) ==========
    hold = Action(kind="HOLD", label="Hold position")
    hold.score = _score_hold(state, sit, p, perc)
    cands.append(hold)

    # ========== ACCIONES DE ATAQUE ==========
    if sit.best_target:
        attack = Action(kind="ATTACK", target=sit.best_target.pos, 
                       label=f"Attack target ({sit.best_target.hp:.1f} HP)")
        attack.score = _score_attack(state, sit, p)
        cands.append(attack)

    # Ordenar por score descendente
    cands.sort(key=lambda a: a.score, reverse=True)
    return cands

def _score_action(state, features, sit, player, dest, perc):
    """
    Calcula score de una acción de movimiento según el estado.
    features: dict con claves safety, away, range, goal, dodge, cover, wall_dist, danger_zone
    """
    w = {
        "EXPLORANDO": {"safety": 0.2, "away": 0.1, "range": 0.0, "goal": 0.4, 
                       "dodge": 0.2, "cover": 0.1, "wall_dist": 0.0, "danger_zone": 0.0},
        "BUSCANDO_OBJETIVO": {"safety": 0.2, "away": 0.1, "range": 0.0, "goal": 0.5, 
                              "dodge": 0.2, "cover": 0.0, "wall_dist": 0.0, "danger_zone": 0.0},
        "ATACANDO": {"safety": 0.1, "away": 0.0, "range": 0.5, "goal": 0.0, 
                     "dodge": 0.2, "cover": 0.1, "wall_dist": 0.1, "danger_zone": 0.0},
        "RETIRÁNDOSE": {"safety": 0.5, "away": 0.3, "range": 0.0, "goal": 0.0, 
                        "dodge": 0.1, "cover": 0.0, "wall_dist": 0.1, "danger_zone": 0.0},
        "BUSCANDO_COBERTURA": {"safety": 0.4, "away": 0.2, "range": 0.0, "goal": 0.0, 
                               "dodge": 0.1, "cover": 0.3, "wall_dist": 0.0, "danger_zone": 0.0},
        "ESCONDIDO": {"safety": 0.8, "away": 0.1, "range": 0.0, "goal": 0.0, 
                      "dodge": 0.1, "cover": 0.0, "wall_dist": 0.0, "danger_zone": 0.0},
        "ESQUIVANDO": {"safety": 0.2, "away": 0.1, "range": 0.0, "goal": 0.0, 
                       "dodge": 0.7, "cover": 0.0, "wall_dist": 0.0, "danger_zone": 0.0},
        "PERSIGUIENDO": {"safety": 0.0, "away": -0.2, "range": 0.3, "goal": 0.2, 
                         "dodge": 0.1, "cover": 0.0, "wall_dist": 0.0, "danger_zone": 0.2},
        "DEFENDIENDO": {"safety": 0.3, "away": 0.0, "range": 0.4, "goal": 0.0, 
                        "dodge": 0.2, "cover": 0.1, "wall_dist": 0.0, "danger_zone": 0.0},
        "RECUPERÁNDOSE": {"safety": 0.6, "away": 0.2, "range": 0.0, "goal": 0.1, 
                          "dodge": 0.1, "cover": 0.0, "wall_dist": 0.0, "danger_zone": 0.0},
    }
    
    weights = w.get(state, w["EXPLORANDO"])
    score = sum(weights.get(k, 0) * features.get(k, 0) for k in weights)
    score /= sum(weights.values()) if sum(weights.values()) > 0 else 1
    
    # Penalizar estar atascado
    if sit.stuck:
        score *= 0.5
    
    # Penalizar zonas peligrosas
    score -= features["danger_zone"] * 0.1
    
    return float(max(0, min(1, score)))

def _score_hold(state, sit, player, perc):
    """Calcula score de mantener posición."""
    score = 0.0
    
    if state == "ESCONDIDO" and sit.threat < 0.3:
        score = 0.8
    elif state == "ATACANDO" and sit.best_target:
        score = 0.6
    elif sit.immediate_danger:
        score = 0.3  # No es recomendable quedarse parado si hay peligro
    else:
        score = 0.2
    
    return float(score)

def _score_attack(state, sit, player):
    """Calcula score de atacar al objetivo."""
    score = 0.0
    
    if not sit.can_shoot:
        return 0.0
    
    if state in ["ATACANDO", "PERSIGUIENDO"]:
        score = 0.9
    elif state == "DEFENDIENDO":
        score = 0.7
    elif state in ["BUSCANDO_OBJETIVO", "BUSCANDO_COBERTURA"]:
        score = 0.4
    else:
        score = 0.2
    
    # Reducir si tiene poca vida
    if sit.hp_low:
        score *= 0.6
    
    # Aumentar si enemigo tiene mucha ventaja
    if sit.enemy_advantage:
        score *= 0.7
    
    return float(max(0, min(1, score)))
