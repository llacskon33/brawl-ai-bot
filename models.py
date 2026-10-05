"""
Modelos de datos del bot.
Define las estructuras de entidades, percepción, situación y decisiones.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Vec = Tuple[float, float]

@dataclass
class Entity:
    """Representa una entidad en pantalla (jugador, enemigo, proyectil)."""
    pos: Vec                          # posición (x, y) en píxeles
    hp: float = 1.0                   # vida 0..1
    vel: Vec = (0.0, 0.0)             # velocidad (vx, vy)
    id: int = -1                      # identificador único
    attacking: bool = False           # está atacando
    approaching: bool = False         # se acerca al jugador
    fleeing: bool = False             # huye del jugador
    wall_between: bool = False        # hay pared entre esta entidad y el jugador
    visible: bool = True              # es visible en el frame actual
    last_seen: float = 0.0            # timestamp del último frame donde fue visto

@dataclass
class Perception:
    """Resultado del análisis visual de una frame."""
    size: Tuple[int, int]             # (ancho, alto) de la imagen
    player: Optional[Entity]          # jugador detectado
    enemies: List[Entity]             # enemigos detectados
    projectiles: List[Entity]         # proyectiles detectados
    goals: List[Vec]                  # objetivos (banderas, gemas, etc.)
    walls: "object"                   # np.ndarray bool, mapa de paredes
    bushes: "object"                  # np.ndarray bool, mapa de arbustos

@dataclass
class Situation:
    """Análisis de la situación táctica actual."""
    threat: float = 0.0               # nivel de amenaza (0..1)
    immediate_danger: bool = False    # peligro inmediato
    hp_low: bool = False              # vida baja
    surrounded: bool = False          # rodeado por enemigos
    stuck: bool = False               # atascado
    near_enemies: int = 0             # número de enemigos cercanos
    cover_nearby: bool = False        # hay cobertura cercana
    incoming: List[Entity] = field(default_factory=list)  # proyectiles entrantes
    best_target: Optional[Entity] = None  # mejor enemigo para atacar
    can_shoot: bool = False           # puede atacar ahora
    enemy_advantage: bool = False     # enemigos tienen ventaja (más vida, más número)

@dataclass
class Action:
    """Acción candidata propuesta por el bot."""
    kind: str                         # MOVE, ATTACK, HOLD
    direction: Vec = (0.0, 0.0)       # dirección (para MOVE)
    target: Optional[Vec] = None      # objetivo (para ATTACK)
    label: str = ""                   # nombre descriptivo
    score: float = 0.0                # puntuación (0..1)

@dataclass
class Decision:
    """Decisión final del bot en un ciclo."""
    state: str                        # estado de la máquina (EXPLORANDO, ATACANDO, etc.)
    action: Action                    # acción elegida
    situation: Situation              # situación evaluada
    candidates: List[Action]          # acciones candidatas consideradas
    reason: str                       # explicación de la decisión
