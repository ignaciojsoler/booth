"""Voz tipo podcast: limpieza de voz con MossFormer2_SE_48K (Apache 2.0) en Modal.

Deploy en CPU (no requiere tarjeta):   modal deploy modal_app.py
Deploy en GPU T4 (requiere tarjeta):   VOICE_GPU=T4 modal deploy modal_app.py
Probar:   modal serve modal_app.py   (URL temporal con recarga en caliente)

Expone:
  GET  /         → healthcheck
  POST /enhance  → body = WAV (mono, cualquier sample rate) · respuesta = WAV limpio
"""
import os

import modal

GPU = os.environ.get("VOICE_GPU") or None   # None → CPU; clearvoice cae a CPU solo si no hay CUDA
# Snapshot de memoria: Modal guarda el proceso con el modelo ya cargado → arranques en frío mucho más cortos.
# Solo en CPU: durante la fase de snapshot no hay GPU, y el modelo quedaría cargado en CPU.
SNAP = GPU is None
MODEL = "MossFormer2_SE_48K"
ROOT = "/models"            # clearvoice busca los pesos en ./checkpoints/<modelo> relativo al cwd
MAX_SECONDS = 180


def download_weights():
    # Se ejecuta al construir la imagen: los pesos quedan horneados y el arranque en frío no los descarga.
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=f"alibabasglab/{MODEL}", local_dir=f"{ROOT}/checkpoints/{MODEL}")


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    # versiones fijadas: torchaudio >= 2.9 cambió su API de I/O y clearvoice depende de la anterior
    .pip_install("torch==2.5.1", "torchaudio==2.5.1", "torchvision==0.20.1")
    .pip_install("clearvoice==0.1.2", "fastapi[standard]")
    .run_function(download_weights)
)

app = modal.App("ai-demos-voice", image=image)


@app.cls(
    gpu=GPU,
    cpu=4.0,                 # en modo CPU, más núcleos = inferencia más rápida
    memory=4096,
    scaledown_window=60,     # se apaga tras 60 s sin uso → no gasta crédito en reposo
    max_containers=1,        # tope de concurrencia: nadie puede escalar tu gasto
    timeout=300,
    enable_memory_snapshot=SNAP,
)
class Voice:
    @modal.enter(snap=SNAP)
    def load(self):
        import os
        os.chdir(ROOT)
        from clearvoice import ClearVoice
        self.cv = ClearVoice(task="speech_enhancement", model_names=[MODEL])

    @modal.asgi_app()
    def web(self):
        import glob
        import os
        import tempfile

        import soundfile as sf
        from fastapi import FastAPI, HTTPException, Request, Response
        from fastapi.middleware.cors import CORSMiddleware

        api = FastAPI()
        api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

        @api.get("/")
        def health():
            return {"ok": True, "model": MODEL}

        @api.post("/enhance")
        async def enhance(request: Request):
            data = await request.body()
            if not data or len(data) > 40 * 1024 * 1024:
                raise HTTPException(400, "Audio vacío o demasiado grande")
            with tempfile.TemporaryDirectory() as d:
                src = os.path.join(d, "input.wav")
                with open(src, "wb") as f:
                    f.write(data)
                try:
                    duration = sf.info(src).duration
                except Exception:
                    raise HTTPException(400, "No es un WAV válido")
                if duration > MAX_SECONDS:
                    raise HTTPException(400, f"Máximo {MAX_SECONDS} segundos")

                out_dir = os.path.join(d, "out")
                # online_write=True deja que clearvoice escriba el archivo con su propio manejo de sample rate
                self.cv(input_path=src, online_write=True, output_path=out_dir)
                files = glob.glob(os.path.join(out_dir, "**", "*.wav"), recursive=True)
                if not files:
                    raise HTTPException(500, "El modelo no devolvió audio")
                with open(files[0], "rb") as f:
                    return Response(f.read(), media_type="audio/wav")

        return api
