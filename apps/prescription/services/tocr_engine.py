import os
import re

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageOps, ImageEnhance
    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    TROCR_AVAILABLE = True
except Exception as e:
    print("TrOCR import error:", e)
    TROCR_AVAILABLE = False


MODEL_NAME = "microsoft/trocr-small-handwritten"

_processor = None
_model = None
_device = None


def load_trocr_model():
    global _processor, _model, _device

    if not TROCR_AVAILABLE:
        return None, None, None

    if _processor is not None and _model is not None:
        return _processor, _model, _device

    try:
        print("Loading TrOCR handwriting model...")

        _device = "cuda" if torch.cuda.is_available() else "cpu"

        _processor = TrOCRProcessor.from_pretrained(MODEL_NAME)
        _model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
        _model.to(_device)
        _model.eval()

        print("TrOCR loaded successfully on:", _device)

        return _processor, _model, _device

    except Exception as e:
        print("TrOCR loading failed:", e)
        return None, None, None


def pil_image_from_django_file(image_file):
    try:
        image_file.seek(0)
        image = Image.open(image_file).convert("RGB")
        return image
    except Exception as e:
        print("PIL image load error:", e)
        return None


def enhance_pil_image(image):
    try:
        image = ImageOps.exif_transpose(image)
        image = ImageOps.autocontrast(image)

        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        return image.convert("RGB")

    except Exception as e:
        print("Image enhancement error:", e)
        return image


def detect_text_line_crops(pil_image):
    """
    TrOCR works better on line-level handwriting.
    This function tries to split prescription image into text-line crops.
    If line detection fails, it returns the full image.
    """

    try:
        image = np.array(pil_image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        gray = cv2.resize(
            gray,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC
        )

        blur = cv2.GaussianBlur(gray, (3, 3), 0)

        thresh = cv2.threshold(
            blur,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )[1]

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 5))

        dilated = cv2.dilate(
            thresh,
            kernel,
            iterations=2
        )

        contours, _ = cv2.findContours(
            dilated,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        boxes = []

        height, width = gray.shape

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            if w < 40 or h < 10:
                continue

            if w > width * 0.95 and h > height * 0.90:
                continue

            pad_x = 20
            pad_y = 15

            x1 = max(x - pad_x, 0)
            y1 = max(y - pad_y, 0)
            x2 = min(x + w + pad_x, width)
            y2 = min(y + h + pad_y, height)

            boxes.append((x1, y1, x2, y2))

        boxes = sorted(
            boxes,
            key=lambda box: box[1]
        )

        line_images = []

        for box in boxes[:12]:
            x1, y1, x2, y2 = box
            crop = gray[y1:y2, x1:x2]

            crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)
            crop_pil = Image.fromarray(crop)
            crop_pil = enhance_pil_image(crop_pil)

            line_images.append(crop_pil)

        if not line_images:
            return [enhance_pil_image(pil_image)]

        print("Detected text lines:", len(line_images))

        return line_images

    except Exception as e:
        print("Text line detection error:", e)
        return [enhance_pil_image(pil_image)]


def clean_trocr_output(text):
    if not text:
        return ""

    text = str(text)
    text = text.replace("|", " ")
    text = re.sub(r"[^A-Za-z0-9\-./,%+ ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def recognize_single_image(pil_image):
    processor, model, device = load_trocr_model()

    if processor is None or model is None:
        return ""

    try:
        pil_image = enhance_pil_image(pil_image)

        pixel_values = processor(
            images=pil_image,
            return_tensors="pt"
        ).pixel_values.to(device)

        with torch.no_grad():
            generated_ids = model.generate(
                pixel_values,
                max_length=64,
                num_beams=4,
                early_stopping=True
            )

        generated_text = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        return clean_trocr_output(generated_text)

    except Exception as e:
        print("TrOCR recognition error:", e)
        return ""


def extract_trocr_text_from_file(image_file):
    if not TROCR_AVAILABLE:
        print("TrOCR is not available.")
        return ""

    pil_image = pil_image_from_django_file(image_file)

    if pil_image is None:
        return ""

    line_images = detect_text_line_crops(pil_image)

    extracted_lines = []

    for index, line_image in enumerate(line_images):
        text = recognize_single_image(line_image)

        print(f"TrOCR line {index + 1}:", text)

        if text and len(text) >= 2:
            extracted_lines.append(text)

    final_text = "\n".join(extracted_lines).strip()

    print("-------- TROCR FINAL TEXT START --------")
    print(final_text)
    print("--------- TROCR FINAL TEXT END ---------")

    return final_text