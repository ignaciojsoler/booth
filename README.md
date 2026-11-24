# Booth — studio voice, anywhere

Subí un audio o video grabado con el celular: la IA (MossFormer2, Apache 2.0) saca el ruido y una cadena de masterización en el navegador le da sonido de podcast (EQ, compresor, normalización, limitador). Comparación A/B y descarga.

- **Frontend:** estático en Cloudflare Pages (`public/`).
- **IA:** endpoint en Modal (`modal_app.py`), en CPU por defecto (sin tarjeta), se apaga solo sin uso.

## Backend (Modal)

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install modal && modal setup   # una vez
modal deploy modal_app.py          # imprime la URL del endpoint
python warm.py on|off              # mantener caliente los días que esperás visitas (~$0.22/h)
```

Pegá la URL en `DEFAULT_ENDPOINT` (en `public/index.html`).

## Frontend (Cloudflare Pages)

```bash
bun install
bunx wrangler login                # una vez
bun run deploy
```

**Ejemplo precargado:** procesá un audio que suene bien, descargá "Original" y "Solo IA" y guardalos como `public/samples/ejemplo-original.wav` y `public/samples/ejemplo-ia.wav`.
