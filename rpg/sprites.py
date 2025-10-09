
import os, math, pygame
from PIL import Image, ImageSequence


DIRS = ["E","SE","S","SW","W","NW","N","NE"]

def _pil_to_surface(frame, scale=1.0):
    f = frame.convert("RGBA")
    surf = pygame.image.fromstring(f.tobytes(), f.size, "RGBA").convert_alpha()
    if scale != 1.0:
        w = int(surf.get_width()*scale); h = int(surf.get_height()*scale)
        surf = pygame.transform.scale(surf, (w, h))
    return surf

def load_gif_frames(path, scale=1.0):
    im = Image.open(path)
    return [_pil_to_surface(f, scale) for f in ImageSequence.Iterator(im)]

def split_8dir(frames):

    if len(frames) >= 8 and len(frames) % 8 == 0:
        per = len(frames)//8
        return [frames[i*per:(i+1)*per] for i in range(8)]
    if len(frames) == 8:
        return [[f] for f in frames]
    return [frames[:] for _ in range(8)]

def dir4_from_vec(v: pygame.Vector2) -> str:
    if abs(v.x) >= abs(v.y):
        return "E" if v.x >= 0 else "W"
    else:
        return "S" if v.y >= 0 else "N"

def dir8_index_from_vec(v: pygame.Vector2) -> int:
    # tsagiin zuunii daguu ergene
    if v.length_squared() == 0: return 2  # default south
    ang = (math.degrees(math.atan2(v.y, v.x)) + 360.0) % 360.0
    return int((ang + 22.5) // 45) % 8

def build_run4(paths: dict, scale=1.0, auto_flip=True, fallback_to_e=True):

    run = {}

    # East
    e_path = paths.get("E")
    run["E"] = load_gif_frames(e_path, scale) if (e_path and os.path.isfile(e_path)) else []

    # West
    w_path = paths.get("W")
    if w_path and os.path.isfile(w_path):
        run["W"] = load_gif_frames(w_path, scale)
    elif auto_flip and run["E"]:
        run["W"] = [pygame.transform.flip(f, True, False) for f in run["E"]]
    else:
        run["W"] = []

    # North / South
    # for d in ("N", "S"):
    #     p = paths.get(d)
    #     if p and os.path.isfile(p):
    #         run[d] = load_gif_frames(p, scale)
    #     elif fallback_to_e and run["E"]:
    #         run[d] = run["E"][:]  # reuse east frames as a fallback
    #     else:
    #         run[d] = []

    return run

def reorder_8(frames_by_dir, gif_order):

    name_to_idx = {name: i for i, name in enumerate(gif_order)}
    out = []
    for name in DIRS:
        idx = name_to_idx.get(name, None)
        out.append(frames_by_dir[idx] if idx is not None else frames_by_dir[0])
    return out