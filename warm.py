"""Mantener el servidor de voz caliente (sin arranque en frío) mientras alguien puede abrir la demo.

  python warm.py on    → 1 contenedor siempre prendido (~$0.22/h en CPU; ~5 días con los $30 gratis)
  python warm.py off   → vuelve a apagarse solo tras 60 s sin uso
"""
import sys

import modal

state = sys.argv[1] if len(sys.argv) > 1 else ""
if state not in ("on", "off"):
    sys.exit(__doc__)

Voice = modal.Cls.from_name("ai-demos-voice", "Voice")
Voice().update_autoscaler(min_containers=1 if state == "on" else 0)
print("Servidor caliente: 1 contenedor fijo" if state == "on" else "Servidor en modo ahorro (se apaga tras 60 s)")
