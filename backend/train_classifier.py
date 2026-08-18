import os
import random
import shutil

from ultralytics import YOLO

# ============================================================
#  Configuration
# ============================================================
ROOT = r"C:\Users\Ghofrane\OneDrive\Desktop\depo-stok-"
FLAT_DATASET = os.path.join(ROOT, "dataset")
STAGED_DIR = os.path.join(ROOT, "dataset_yolo")
MODEL_OUT = os.path.join(ROOT, "backend", "models", "box_classifier.pt")

#  (folder_name, class_index, product_id)
#  ultralytics uses alphabetical / prefix ordering to set class indices,
#  so we prefix folders with "00_", "01_" etc. to force the exact order.
CLASS_ORDER = [
    ("elektronik",  0, 1),
    ("gida",        1, 2),
    ("tekstil",     2, 3),
    ("kirtasiye",   3, 4),
    ("temizlik",    4, 5),
]

SPLITS = {"train": 0.8, "val": 0.2}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
EPOCHS = 15
IMG_SIZE = 224
BATCH = 16
LR0 = 0.001          # initial learning rate (lower default helps small datasets)


# ============================================================
#  1. Stage the dataset into YOLO-cls expected layout:
#     dataset_yolo/
#       train/
#         00_elektronik/
#         01_gida/
#         ...
#       val/
#         00_elektronik/
#         ...
# ============================================================
def stage_dataset():
    if os.path.isdir(STAGED_DIR):
        shutil.rmtree(STAGED_DIR)
    os.makedirs(STAGED_DIR)

    for folder_name, cls_idx, _ in CLASS_ORDER:
        src_dir = os.path.join(FLAT_DATASET, folder_name)
        if not os.path.isdir(src_dir):
            print(f"  [WARN] Source folder not found: {src_dir}")
            continue

        images = [
            f for f in os.listdir(src_dir)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS
        ]
        random.shuffle(images)

        train_count = int(len(images) * SPLITS["train"])
        splits = {
            "train": images[:train_count],
            "val": images[train_count:],
        }

        for split_name, file_list in splits.items():
            dest = os.path.join(STAGED_DIR, split_name, f"{cls_idx:02d}_{folder_name}")
            os.makedirs(dest, exist_ok=True)
            for fname in file_list:
                shutil.copy2(os.path.join(src_dir, fname), os.path.join(dest, fname))

    print("Dataset staged for YOLO-cls:")
    for split in ["train", "val"]:
        split_dir = os.path.join(STAGED_DIR, split)
        if os.path.isdir(split_dir):
            counts = {
                d: len(os.listdir(os.path.join(split_dir, d)))
                for d in os.listdir(split_dir)
                if os.path.isdir(os.path.join(split_dir, d))
            }
            total = sum(counts.values())
            print(f"  {split}: {total} images across {len(counts)} classes")


# ============================================================
#  2. Train
# ============================================================
def train(dataset_dir):
    model = YOLO("yolov8n-cls.pt")

    results = model.train(
        data=dataset_dir,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        lr0=LR0,
        name="box_classifier",
        exist_ok=True,
        verbose=True,
        # --- data augmentation (YOLO defaults, made explicit) ---
        hsv_h=0.015,       # HSV-Hue augmentation
        hsv_s=0.7,         # HSV-Saturation augmentation
        hsv_v=0.4,         # HSV-Value augmentation
        degrees=10.0,      # rotation +/- degrees
        translate=0.1,     # translation
        scale=0.5,         # scale augmentation
        fliplr=0.5,        # horizontal flip probability
        mosaic=1.0,        # mosaic augmentation (classification)
        erasing=0.2,       # random erasing during training
    )
    return model, results


# ============================================================
#  4. Validate and return accuracy
# ============================================================
def validate(model, dataset_dir):
    metrics = model.val(data=dataset_dir)
    return metrics


# ============================================================
#  5. Export best weights to the final path
# ============================================================
def export_model():
    best = os.path.join(ROOT, "runs", "classify", "train", "weights", "best.pt")
    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    shutil.copy2(best, MODEL_OUT)
    print(f"\nBest model saved to: {MODEL_OUT}")


# ============================================================
#  6. Print summary
# ============================================================
def print_summary(val_metrics):
    acc = val_metrics.top1 if val_metrics else None
    print("\n" + "=" * 55)
    print("  TRAINING COMPLETE")
    print("=" * 55)
    if acc is not None:
        print(f"  Final Validation Accuracy (top-1): {acc * 100:.2f}%")
    print()
    print("  Class-Index -> Product-ID Mapping")
    print("-" * 55)
    print(f"  {'Class Index':<14} {'Folder':<14} {'Product ID':<12}")
    print("-" * 55)
    for folder, cls_idx, pid in CLASS_ORDER:
        print(f"  {cls_idx:<14} {folder:<14} {pid:<12}")
    print("=" * 55)


# ============================================================
#  Main
# ============================================================
def main():
    print("Step 1/4: Staging dataset ...")
    stage_dataset()

    print(f"\nStep 2/4: Training YOLOv8-cls ({EPOCHS} epochs, img={IMG_SIZE}, batch={BATCH}) ...")
    print("  (This will take ~25-40 minutes on CPU. Be patient.)\n")
    model, results = train(STAGED_DIR)

    print("\nStep 3/4: Running final validation ...")
    val_metrics = validate(model, STAGED_DIR)

    print("\nStep 4/4: Exporting best model ...")
    export_model()

    print_summary(val_metrics)
    print("Done.")


if __name__ == "__main__":
    main()
