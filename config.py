"""
Configuración central del bot.
Define umbrales, rangos de color HSV, pesos y constantes.
"""

CELL = 16  # tamaño de celda de la rejilla (px)

# Rangos HSV para detección de colores (placeholder: calibrar con capturas reales)
HSV = {
    "player": ((95, 120, 120), (115, 255, 255)),   # azul
    "enemy":  ((0, 150, 120), (10, 255, 255)),     # rojo
    "bush":   ((40, 80, 60), (75, 255, 180)),      # verde
    "wall":   ((10, 40, 60), (25, 160, 170)),      # marrón
    "proj":   ((20, 150, 200), (35, 255, 255)),    # amarillo
    "goal":   ((140, 100, 120), (165, 255, 255)),  # magenta
}

MIN_AREA = 30  # píxeles mínimos para considerar una entidad

# Distancias (píxeles)
ATTACK_RANGE = 260        # alcance de ataque
SAFE_DISTANCE = 180       # distancia segura de enemigos
DANGER_DISTANCE = 90      # peligro inmediato

# Estado del jugador
LOW_HP = 0.35             # vida baja (35% o menos)

# Memoria
MEMORY_TTL = 4.0          # segundos que se recuerda un enemigo no visible
DANGER_ZONE_TTL = 8.0     # segundos que se recuerda una zona peligrosa
HIDE_MIN_TIME = 1.5       # segundos mínimos escondido
HIDE_MAX_TIME = 6.0       # segundos máximos escondido

# Movimiento
NOISE = 0.15              # variación aleatoria en el movimiento (0..1)
STUCK_THRESHOLD = 3       # ciclos atascado antes de cambiar ruta
