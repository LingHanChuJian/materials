from settings.settings import settings

def pixel_to_mm(pixel: int) -> float:
    return pixel * 25.4 / settings.dpi

def mm_to_pixel(mm: float) -> int:
    return int(mm * settings.dpi / 25.4)
