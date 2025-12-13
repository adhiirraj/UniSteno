# diagnostics.py
from PIL import Image
import numpy as np
from pathlib import Path

orig = Path("uploads/some_image_2.png")
out  = Path("uploads/embedded_some_image_2.png")

for p in [orig, out]:
    print("====", p)
    im = Image.open(p)
    print("mode, size, format:", im.mode, im.size, im.format)
    arr = np.array(im)
    print("dtype, shape, min, max, mean:", arr.dtype, arr.shape, int(arr.min()), int(arr.max()), float(arr.mean()))
    flat = arr.ravel()
    nonzero = int((flat != 0).sum())
    print("nonzero bytes / total:", nonzero, "/", flat.size)
    print("first 40 raw bytes:", flat[:40].tolist())
    if arr.ndim == 3:
        print("first 12 pixels (R,G,B):", arr.reshape(-1, arr.shape[-1])[:12].tolist())
    else:
        print("first 12 pixels (gray):", arr.ravel()[:12].tolist())
    print()
