# Sample Assets

CineAnchor V0.1 requires a PNG image for `character_intro` and a GLB model
for `product_orbit` to render promotional videos.

## Placing Sample Assets

Place your assets in this directory:

```
samples/
├── README.md
└── assets/
    ├── hero.png      ← transparent PNG character for character_intro
    └── model.glb     ← GLB 3D model for product_orbit
```

### hero.png

- A transparent PNG character image (e.g., game character, mascot)
- Recommended: 512×1024 or larger, with clear alpha channel
- The character should be roughly centered in frame
- Non-transparent backgrounds will render as a white rectangle

### model.glb

- A GLB (glTF Binary) 3D model
- Recommended: under 500K triangles for fast rendering
- Textures should be embedded or referenced relative to the GLB
- Free sources: Sketchfab (download as glTF), Poly Pizza, Quaternius

## License Note

Sample assets are NOT committed to the repository. You must provide your own
assets or download free samples. The repository `.gitignore` covers all files
under `samples/assets/` except this README.

## Testing Without Assets

If you don't have sample assets, you can still:

- Run unit tests: `scripts\run_tests.bat` (no assets required)
- Start the server and upload your own files through the Web UI

For release smoke verification, `scripts\golden_smoke.py` also accepts explicit
asset paths:

```powershell
$env:CINEANCHOR_SMOKE_URL="http://127.0.0.1:8000"
$env:CINEANCHOR_SAMPLE_PNG="E:\path\to\hero.png"
$env:CINEANCHOR_SAMPLE_GLB="E:\path\to\model.glb"
.\.venv\Scripts\python.exe scripts\golden_smoke.py
```

The script prints clear `SKIP` messages when sample assets are missing.
