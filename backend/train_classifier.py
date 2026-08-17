import os
import random
import shutil
import yaml

from ultralytics import YOLO

# ============================================================
#  Configuration
# ============================================================
ROOT = r"C:\Users\Ghofrane\OneDrive\Desktop\depo-stok-"
FLAT_DATASET = os.path.join(ROOT, "dataset")
STAGED_DIR = os.path.join(ROOT, "dataset_yolo")
MODEL_OUT = os.path.join(ROOT, "backend", "models", "box_classifier.pt")

#  Alphabetical folder name -> (forced class index, product_id)
#  We prefix class folders with "00_", "01_" ... so ultralytics
#  picks them up in exactly this index order.
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
#  2. Write the YAML config ultralytics expects
# ============================================================
def write_yaml():
    yaml_path = os.path.join(STAGED_DIR, "data.yaml")
    config = {
        "path": STAGED_DIR,
        "train": "train",
        "val": "val",
        "names": {cls_idx: folder for folder, cls_idx, _ in CLASS_ORDER},
    }
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    return yaml_path


# ============================================================
#  3. Train
# ============================================================
def train(yaml_path):
    model = YOLO("yolov8n-cls.pt")

    results = model.train(
        data=yaml_path,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        name="box_classifier",
        exist_ok=True,
        verbose=True,
    )
    return results


# ============================================================
#  4. Export best weights to the final path
# ============================================================
def export_model():
    best = os.path.join(ROOT, "runs", "classify", "train", "weights", "best.pt")
    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    shutil.copy2(best, MODEL_OUT)
    print(f"\nBest model saved to: {MODEL_OUT}")


# ============================================================
#  5. Print summary
# ============================================================
def print_summary():
    print("\n" + "=" * 55)
    print("  Class-Index -> Product-ID Mapping")
    print("=" * 55)
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

    print("\nStep 2/4: Writing data.yaml ...")
    yaml_path = write_yaml()

    print("\nStep 3/4: Training YOLOv8-cls (this will take a while on CPU) ...\n")
    train(yaml_path)

    print("\nStep 4/4: Exporting best model ...")
    export_model()

    print_summary()
    print("Done.")


if __name__ == "__main__":
    main()
