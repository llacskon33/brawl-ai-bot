"""
Cerebro del bot (Apartado 8).
Integra percepción, análisis, generación de acciones y toma de decisiones.
"""

import time
from perception import perceive
from memory import Memory
from analysis import analyze
from actions import generate
from state_machine import StateMachine
from models import Decision, Action

class Brain:
    """Cerebro del bot: orquesta todo el pipeline de decisiones."""
    
    def __init__(self):
        self.memory = Memory()
        self.state_machine = StateMachine()
        self.last_decision = None
        self.cycle_count = 0

    def think(self, img_bgr) -> Decision:
        """
        Ciclo completo de decisión:
        1. Percepción visual
        2. Actualizar memoria
        3. Análisis de situación
        4. Generar acciones candidatas
        5. Elegir mejor acción según estado
        
        Args:
            img_bgr: imagen en formato BGR
        
        Returns:
            Decision con acción elegida y justificación
        """
        now = time.time()
        self.cycle_count += 1
        
        # 1. PERCEPCIÓN
        perc = perceive(img_bgr)
        
        # 2. ACTUALIZAR MEMORIA
        self.memory.update(perc, now)
        
        # 3. ANÁLISIS TÁCTICO
        sit = analyze(perc, self.memory, now)
        
        # 4. GENERAR ACCIONES
        candidates = generate(perc, self.memory, sit, self.state_machine.current)
        
        # 5. ELEGIR ACCIÓN
        if not perc.player:
            action = Action(kind="HOLD", label="No player detected")
            reason = "Jugador no detectado"
        elif not candidates:
            action = Action(kind="HOLD", label="No valid actions")
            reason = "Sin acciones válidas"
        else:
            action = candidates[0]  # La mejor (score más alto)
            reason = f"Score: {action.score:.2f}"
        
        # 6. ACTUALIZAR MÁQUINA DE ESTADOS
        state = self.state_machine.update(sit)
        
        # 7. CREAR DECISIÓN
        decision = Decision(
            state=state,
            action=action,
            situation=sit,
            candidates=candidates[:5],  # Top 5
            reason=reason
        )
        
        self.last_decision = decision
        self.memory.last_action = action
        return decision

    def get_status(self) -> dict:
        """Devuelve estado actual del bot para la interfaz."""
        if not self.last_decision:
            return {"status": "waiting"}
        
        d = self.last_decision
        p = d.situation
        
        return {
            "status": "thinking",
            "cycle": self.cycle_count,
            "state": d.state,
            "action": d.action.label,
            "score": d.action.score,
            "reason": d.reason,
            "threat": p.threat,
            "hp_low": p.hp_low,
            "immediate_danger": p.immediate_danger,
            "near_enemies": p.near_enemies,
            "surrounded": p.surrounded,
            "cover_nearby": p.cover_nearby,
            "incoming": len(p.incoming),
            "can_shoot": p.can_shoot,
            "candidates": [
                {"label": c.label, "score": c.score}
                for c in d.candidates
            ]
        }
