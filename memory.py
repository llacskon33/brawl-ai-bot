"""
Módulo de memoria (Apartados 3 y 10).
Mantiene seguimiento de enemigos no visibles, zonas peligrosas y estado.
"""

import math
import time
from config import MEMORY_TTL, DANGER_ZONE_TTL
from models import Entity

def dist(a, b):
    """Distancia euclídea entre dos puntos."""
    return math.hypot(a[0] - b[0], a[1] - b[1])

class Memory:
    """Almacena memoria del bot entre frames."""
    
    def __init__(self):
        self.enemies = {}                # id -> Entity (incluye no visibles)
        self.next_id = 0                 # contador para IDs de enemigos
        self.danger_zones = []           # lista de (pos, timestamp)
        self.cover_spots = []            # lugares donde se encontró cobertura
        self.last_action = None          # última acción ejecutada
        self.last_result = ""            # resultado de la última acción
        self.prev_player = None          # posición anterior del jugador
        self.prev_player_hp = None       # vida anterior del jugador
        self.stuck_counter = 0           # contador de frames atascado
        self.projectiles_prev = []       # proyectiles del frame anterior
        self.state_since = time.time()   # cuándo entró en el estado actual

    def update(self, perc, now=None):
        """
        Actualiza la memoria con nueva percepción.
        Empareja enemigos detectados con los conocidos, actualiza posiciones y velocidades.
        """
        now = now or time.time()
        
        # Marcar todos los enemigos como no visibles inicialmente
        for e in self.enemies.values():
            e.visible = False
        
        # Procesar enemigos detectados en este frame
        for det in perc.enemies:
            # Buscar enemigo conocido más cercano
            match, best = None, 80
            for e in self.enemies.values():
                d = dist(e.pos, det.pos)
                if d < best:
                    match, best = e, d
            
            if match is None:
                # Nuevo enemigo
                det.id = self.next_id
                self.next_id += 1
                det.last_seen = now
                self.enemies[det.id] = det
                continue
            
            # Actualizar enemigo existente
            dt = max(1e-3, now - match.last_seen)
            vel = ((det.pos[0] - match.pos[0]) / dt, (det.pos[1] - match.pos[1]) / dt)
            
            # Detectar si se acerca o huye
            p = perc.player.pos if perc.player else None
            if p:
                before = dist(match.pos, p)
                after = dist(det.pos, p)
                match.approaching = after < before - 2
                match.fleeing = after > before + 2
            
            match.vel = vel
            match.pos = det.pos
            match.hp = det.hp
            match.visible = True
            match.last_seen = now
        
        # Limpiar enemigos que no se han visto en mucho tiempo
        self.enemies = {i: e for i, e in self.enemies.items()
                        if now - e.last_seen < MEMORY_TTL}

        # Estimar velocidad de proyectiles comparando con frame anterior
        for pr in perc.projectiles:
            near = min(self.projectiles_prev, 
                      key=lambda q: dist(q.pos, pr.pos), default=None)
            if near and dist(near.pos, pr.pos) < 120:
                pr.vel = (pr.pos[0] - near.pos[0], pr.pos[1] - near.pos[1])
        self.projectiles_prev = perc.projectiles

        # Detectar si está atascado
        if perc.player:
            moved = self.prev_player and dist(self.prev_player, perc.player.pos) < 2
            wants_move = self.last_action and self.last_action.kind == "MOVE"
            self.stuck_counter = self.stuck_counter + 1 if (moved and wants_move) else 0
            
            # Registrar zonas peligrosas donde recibió daño
            if self.prev_player_hp is not None:
                lost = self.prev_player_hp - perc.player.hp
                if lost > 0.03:
                    self.danger_zones.append((perc.player.pos, now))
                    self.last_result = f"daño recibido (-{lost:.2f})"
                else:
                    self.last_result = "sin daño"
            
            self.prev_player = perc.player.pos
            self.prev_player_hp = perc.player.hp
        
        # Limpiar zonas peligrosas antiguas
        self.danger_zones = [(p, t) for p, t in self.danger_zones
                             if now - t < DANGER_ZONE_TTL]

    def remember_cover(self, pos):
        """Registra una posición de cobertura encontrada."""
        self.cover_spots.append((pos, time.time()))
        self.cover_spots = self.cover_spots[-10:]

    def visible_enemies(self):
        """Devuelve lista de enemigos visibles."""
        return [e for e in self.enemies.values() if e.visible]
