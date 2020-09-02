import os
from PIL import Image

CUR_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_IMGS = ['logo.png', 'logo_monochrome.png']
SIZES = [16, 32, 64, 128, 256, 512, 1024]


def main():
    for size in SIZES:
        dir_path = os.path.join(CUR_DIR, f"{size}x{size}")
        os.mkdir(dir_path)

        for img in BASE_IMGS:
            image = Image.open(os.path.join(CUR_DIR, img))
            image.thumbnail((size, size))
            image.save(os.path.join(dir_path, img))


if __name__ == '__main__':
    main()
