"""Extract and cache bitmap resources from SCW.EXE / SCWTIT.DLL.

NE (New Executable) resources are raw DIBs with no BITMAPFILEHEADER.
We prepend the 14-byte header on the fly and load via BytesIO so no
temp files are needed.  All surfaces are cached after first load.

Usage:
    from second_conflict.assets import get_bitmap, get_star_sprite

    surf = get_bitmap(27)            # bitmap resource 27 from SCW.EXE
    surf = get_bitmap(1, 'SCWTIT.DLL')
"""
import io
import os
import struct

import pygame

_cache: dict[tuple[str, int], pygame.Surface | None] = {}
_bitmaps: dict[str, dict[int, tuple[int, int]]] = {}  # file → {res_id: (offset, length)}


def _game_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, '..', 'second-conflict')


def _index_ne(path: str) -> dict[int, tuple[int, int]]:
    """Parse NE resource table; return {res_id: (offset, length)} for BITMAPs."""
    result = {}
    try:
        data = open(path, 'rb').read()
        if data[:2] != b'MZ':
            return result
        ne_off = struct.unpack_from('<H', data, 0x3C)[0]
        if data[ne_off:ne_off + 2] != b'NE':
            return result
        rt_off = struct.unpack_from('<H', data, ne_off + 0x24)[0]
        rt_abs = ne_off + rt_off
        align  = struct.unpack_from('<H', data, rt_abs)[0]
        pos    = rt_abs + 2
        while True:
            type_id = struct.unpack_from('<H', data, pos)[0]
            if type_id == 0:
                break
            count = struct.unpack_from('<H', data, pos + 2)[0]
            pos += 8
            for _ in range(count):
                offset = struct.unpack_from('<H', data, pos)[0] << align
                length = struct.unpack_from('<H', data, pos + 2)[0] << align
                res_id = struct.unpack_from('<H', data, pos + 6)[0] & 0x7FFF
                pos += 12
                if type_id == 0x8002:   # RT_BITMAP
                    result[res_id] = (offset, length)
    except Exception:
        pass
    return result


def _load_dib(path: str, offset: int, length: int) -> pygame.Surface | None:
    """Read raw DIB from file, prepend BITMAPFILEHEADER, load as pygame surface."""
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            dib = f.read(length)
        hdr_size    = struct.unpack_from('<I', dib, 0)[0]
        bpp         = struct.unpack_from('<H', dib, 14)[0]
        colors      = struct.unpack_from('<I', dib, 32)[0]
        pal_entries = colors if colors else (2 ** bpp if bpp <= 8 else 0)
        pixel_off   = 14 + hdr_size + pal_entries * 4
        file_size   = 14 + len(dib)
        bfh = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, pixel_off)
        buf = io.BytesIO(bfh + dib)
        surf = pygame.image.load(buf, 'bmp')
        surf = surf.convert()
        surf.set_colorkey((0, 0, 0))
        return surf
    except Exception:
        return None


def _ensure_indexed(filename: str):
    if filename in _bitmaps:
        return
    path = os.path.join(_game_dir(), filename)
    _bitmaps[filename] = _index_ne(path) if os.path.isfile(path) else {}


def get_bitmap(resource_id: int, filename: str = 'SCW.EXE') -> pygame.Surface | None:
    """Return bitmap resource as a pygame.Surface with black colorkey, or None."""
    key = (filename, resource_id)
    if key in _cache:
        return _cache[key]
    _ensure_indexed(filename)
    index = _bitmaps.get(filename, {})
    if resource_id not in index:
        _cache[key] = None
        return None
    path = os.path.join(_game_dir(), filename)
    offset, length = index[resource_id]
    surf = _load_dib(path, offset, length)
    _cache[key] = surf
    return surf


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def get_star_sprite(player_colour: tuple, size: int = 30) -> pygame.Surface | None:
    """Return the star sprite (bitmap 1, 15×15) tinted to player_colour and
    scaled to size×size.  Returns None if SCW.EXE is not found."""
    cache_key = ('_star_tinted', player_colour, size)
    if cache_key in _cache:
        return _cache[cache_key]

    base = get_bitmap(1)   # white star burst, 15×15
    if base is None:
        _cache[cache_key] = None
        return None

    scaled = pygame.transform.scale(base, (size, size))
    tinted = scaled.copy()
    # Multiply each pixel by the player colour: white → player_colour
    overlay = pygame.Surface((size, size))
    overlay.fill(player_colour)
    tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    tinted.set_colorkey((0, 0, 0))

    _cache[cache_key] = tinted
    return tinted


def get_ship_dot(scale: int = 2) -> pygame.Surface | None:
    """Return ship dot sprite (bitmap 28, 7×5) scaled by *scale*.
    Returns None if SCW.EXE is not found."""
    cache_key = ('_ship_dot', scale)
    if cache_key in _cache:
        return _cache[cache_key]

    base = get_bitmap(28)
    if base is None:
        _cache[cache_key] = None
        return None

    w, h = base.get_size()
    surf = pygame.transform.scale(base, (w * scale, h * scale))
    surf.set_colorkey((0, 0, 0))
    _cache[cache_key] = surf
    return surf


def get_title_screen() -> pygame.Surface | None:
    """Return the 288×360 title screen from SCWTIT.DLL, or None."""
    return get_bitmap(1, 'SCWTIT.DLL')