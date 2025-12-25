from PIL import Image
from javsp.cropper.interface import Cropper, DefaultCropper
from javsp.cropper.utils import get_bound_box_by_face

class SlimefaceCropper(Cropper):
    def crop_specific(self, fanart: Image.Image, ratio: float) -> Image.Image:
        try: 
            # defer the libary import so we don't break if missing dependencies 
            from slimeface import detectRGB
            bbox_confs = detectRGB(fanart.width, fanart.height, fanart.convert('RGB').tobytes())
            if not bbox_confs:
                # 如果没有检测到人脸，使用默认裁切
                return DefaultCropper().crop_specific(fanart, ratio)
            bbox_confs.sort(key=lambda conf_bbox: -conf_bbox[4]) # last arg stores confidence
            face = bbox_confs[0][:-1]
            poster_box = get_bound_box_by_face(face, fanart.size, ratio)
            return fanart.crop(poster_box)
        except ImportError:
            # slimeface 库未安装
            raise
        except Exception as e:
            # 其他错误，使用默认裁切
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"人脸识别失败，使用默认裁切: {e}")
            return DefaultCropper().crop_specific(fanart, ratio)

if __name__ == '__main__':
    from argparse import ArgumentParser

    arg_parser = ArgumentParser(prog='slimeface crop')

    arg_parser.add_argument('-i', '--image', help='path to image to detect')

    args, _ = arg_parser.parse_known_args()

    if(args.image is None):
        print("USAGE: slimeface_crop.py -i/--image [path]")
        exit(1)

    input = Image.open(args.image)
    im = SlimefaceCropper().crop(input)
    im.save('output.png')
