import os
from ultralytics import YOLO

# ============================================================
#  Configuration
# ============================================================
ROOT = r"C:\Users\Ghofrane\OneDrive\Desktop\depo-stok-"
MODEL_PATH = os.path.join(ROOT, "backend", "models", "box_classifier.pt")
DATASET = os.path.join(ROOT, "dataset")

#  One sample image per class folder
SAMPLE_IMAGES = [
    "elektronik",
    "gida",
    "tekstil",
    "kirtasiye",
    "temizlik",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}


def first_image(folder: str) -> str | None:
    """Return the first image file found in a dataset subfolder."""
    path = os.path.join(DATASET, folder)
    for f in sorted(os.listdir(path)):
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
            return os.path.join(path, f)
    return None


def main():
    model = YOLO(MODEL_PATH)

    print(f"Loaded model : {MODEL_PATH}")
    print(f"Class names  : {model.names}")
    print("=" * 55)

    for label in SAMPLE_IMAGES:
        img = first_image(label)
        if img is None:
            print(f"  [{label}]  -- no image found, skipped")
            continue

        result = model.predict(source=img, verbose=False)[0]
        top1_idx = int(result.probs.top1)
        top1_conf = float(result.probs.top1conf)
        pred_raw = result.names[top1_idx]
        pred_name = pred_raw.split("_", 1)[-1]       # "01_gida" -> "gida"

        status = "OK" if pred_name == label else "WRONG"
        print(
            f"  {label:<12} -> {pred_name:<12} "
            f"conf={top1_conf:.2%}  [{status}]"
        )

    print("=" * 55)


if __name__ == "__main__":
    main()
