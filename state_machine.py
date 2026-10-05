"""
Máquina de estados del bot (Apartado 9).
Gestiona transiciones entre estados según la situación.
"""

import time
from models import Situation

class StateMachine:
    """
    Estados:
    - EXPLORANDO: buscando acción, sin enemigos visibles
    - BUSCANDO_OBJETIVO: explorando hacia el objetivo del modo
    - ATACANDO: enemigo en rango y es favorable atacar
    - RETIRÁNDOSE: huyendo de enemigos
    - BUSCANDO_COBERTURA: amenaza moderada, buscando cobertura
    - ESCONDIDO: en cobertura esperando que amenaza disminuya
    - ESQUIVANDO: proyectil entrante, evadiendo
    - PERSIGUIENDO: enemigo visible pero fuera de rango, persiguiendo
    - DEFENDIENDO: posición defensiva, protegiendo objetivo
    - RECUPERÁNDOSE: vida baja, esperando recuperarse
    """
    
    STATES = [
        "EXPLORANDO",
        "BUSCANDO_OBJETIVO",
        "ATACANDO",
        "RETIRÁNDOSE",
        "BUSCANDO_COBERTURA",
        "ESCONDIDO",
        "ESQUIVANDO",
        "PERSIGUIENDO",
        "DEFENDIENDO",
        "RECUPERÁNDOSE",
    ]
    
    def __init__(self):
        self.current = "EXPLORANDO"
        self.state_since = time.time()
        self.hide_until = None

    def update(self, sit: Situation) -> str:
        """
        Actualiza el estado según la situación.
        Devuelve el nuevo estado.
        """
        now = time.time()
        time_in_state = now - self.state_since
        
        # Esquivando: proyectil entrante
        if sit.incoming and self.current != "ESQUIVANDO":
            return self._change_state("ESQUIVANDO", now)
        elif self.current == "ESQUIVANDO" and not sit.incoming:
            return self._change_state("EXPLORANDO", now)
        
        # Peligro inmediato
        if sit.immediate_danger:
            if self.current not in ["ESQUIVANDO", "RETIRÁNDOSE", "BUSCANDO_COBERTURA"]:
                return self._change_state("RETIRÁNDOSE", now)
        
        # Recuperándose: vida muy baja
        if sit.hp_low and self.current != "RECUPERÁNDOSE":
            return self._change_state("RECUPERÁNDOSE", now)
        elif sit.hp_low and self.current == "RECUPERÁNDOSE":
            # Permanecer recuperándose
            return self.current
        elif self.current == "RECUPERÁNDOSE" and not sit.hp_low:
            return self._change_state("EXPLORANDO", now)
        
        # Escondido: esperar a que disminuya amenaza
        if self.current == "ESCONDIDO":
            if self.hide_until and now > self.hide_until:
                return self._change_state("EXPLORANDO", now)
            if sit.threat > 0.7:
                self.hide_until = now + 2.0
            return self.current
        
        # Buscando cobertura: amenaza moderada
        if sit.threat > 0.5 and sit.cover_nearby and self.current not in ["ESCONDIDO", "RETIRÁNDOSE"]:
            return self._change_state("BUSCANDO_COBERTURA", now)
        elif self.current == "BUSCANDO_COBERTURA":
            # Una vez en cobertura y amenaza disminuye, esconderse
            if sit.threat > 0.6:
                return self._change_state("ESCONDIDO", now)
            elif sit.threat < 0.3:
                return self._change_state("EXPLORANDO", now)
        
        # Atacando: enemigo en rango y favorable
        if sit.can_shoot and sit.best_target:
            if sit.threat < 0.5 and not sit.enemy_advantage:
                return self._change_state("ATACANDO", now)
        
        # Persiguiendo: enemigo visible pero fuera de rango
        if not sit.can_shoot and sit.best_target and sit.threat > 0.2:
            return self._change_state("PERSIGUIENDO", now)
        elif self.current == "PERSIGUIENDO" and not sit.best_target:
            return self._change_state("BUSCANDO_OBJETIVO", now)
        
        # Retirándose: alejarse de enemigos
        if self.current == "RETIRÁNDOSE":
            if sit.threat < 0.3:
                return self._change_state("EXPLORANDO", now)
            return self.current
        
        # Por defecto: explorar o buscar objetivo
        if self.current in ["EXPLORANDO", "BUSCANDO_OBJETIVO"]:
            if sit.near_enemies > 0:
                return self._change_state("PERSIGUIENDO", now)
            return self.current
        
        # Caso por defecto
        return self._change_state("EXPLORANDO", now)

    def _change_state(self, new_state: str, now=None) -> str:
        """Cambia de estado y registra el tiempo."""
        if new_state != self.current:
            self.current = new_state
            self.state_since = now or time.time()
        return self.current
