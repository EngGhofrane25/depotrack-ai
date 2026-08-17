import os
import random
import shutil

ROOT = r"C:\Users\Ghofrane\OneDrive\Desktop\depo-stok-"
SOURCE = os.path.join(ROOT, "ECOMMERCE_PRODUCT_IMAGES")
DEST = os.path.join(ROOT, "dataset")
SPLITS = ["train", "val", "check"]
MAX_IMAGES = 100

MAPPING = {
    "elektronik": "ELECTRONICS",
    "gida": "GROCERY",
    "tekstil": "CLOTHING_ACCESSORIES_JEWELLERY",
    "kirtasiye": "HOBBY_ARTS_STATIONERY",
    "temizlik": "HOME_KITCHEN_TOOLS",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}


def collect_images(dest_name, source_folder):
    all_images = []
    for split in SPLITS:
        folder = os.path.join(SOURCE, split, source_folder)
        if not os.path.isdir(folder):
            print(f"  [WARN] Missing folder: {folder}")
            continue
        for fname in os.listdir(folder):
            if os.path.splitext(fname)[1].lower() in IMAGE_EXTS:
                all_images.append(os.path.join(folder, fname))
    return all_images


def main():
    os.makedirs(DEST, exist_ok=True)

    print("=" * 55)
    print("  Dataset Preparation — Summary")
    print("=" * 55)

    for dest_name, source_folder in MAPPING.items():
        dest_dir = os.path.join(DEST, dest_name)
        os.makedirs(dest_dir, exist_ok=True)

        images = collect_images(dest_name, source_folder)
        total_found = len(images)

        if total_found > MAX_IMAGES:
            images = random.sample(images, MAX_IMAGES)

        for idx, src_path in enumerate(images, start=1):
            ext = os.path.splitext(src_path)[1].lower()
            dst_path = os.path.join(dest_dir, f"{dest_name}_{idx:03d}{ext}")
            shutil.copy2(src_path, dst_path)

        copied = len(images)
        print(f"  {dest_name:<12} : {copied:>4} images  (found {total_found} across splits)")

    print("=" * 55)
    print(f"  Done. Files saved to: {DEST}")
    print("=" * 55)


if __name__ == "__main__":
    main()
