"""Scenario picker dialog.

Searches standard locations for SCWSCEN.* and *.SCN files, shows a
selectable list with player count and names, and returns the path chosen
(or None if cancelled).

Search order:
  1. Directory of SCW.EXE / SCWTIT.DLL if found on PATH or alongside the
     running script
  2. ./second-conflict/   (development layout)
  3. ./scenarios/
  4. .  (current working directory)
"""
import os
import sys
import glob
import struct
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL

_ROW_H   = 20
_HDR_COL = (160, 160, 210)
_SEL_COL = (50, 70, 120)
_ALT_COL = (18, 22, 36)

# Bytes needed for a quick header parse (enough to read player names)
_QUICK_PARSE_BYTES = 20000


def _search_dirs() -> list[str]:
    """Return candidate directories to search for scenario files."""
    dirs = []
    # Alongside the running script / exe
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    dirs.append(script_dir)
    # Dev layout: project root / second-conflict
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    dirs.append(os.path.join(project_root, 'second-conflict'))
    dirs.append(os.path.join(project_root, 'scenarios'))
    dirs.append(project_root)
    # cwd
    dirs.append(os.getcwd())
    return dirs


def _find_scenarios() -> list[str]:
    """Return sorted list of unique scenario file paths."""
    seen: set[str] = set()
    paths: list[str] = []
    for d in _search_dirs():
        if not os.path.isdir(d):
            continue
        for pattern in ('SCWSCEN.*', 'scwscen.*', '*.SCN', '*.scn'):
            for p in sorted(glob.glob(os.path.join(d, pattern))):
                norm = os.path.normcase(os.path.abspath(p))
                if norm not in seen and os.path.isfile(p):
                    seen.add(norm)
                    paths.append(p)
    return paths


def _quick_meta(path: str) -> tuple[int, list[str]]:
    """Extract (num_players, [name, ...]) without a full parse."""
    try:
        with open(path, 'rb') as f:
            data = f.read(_QUICK_PARSE_BYTES)

        # Header byte[6] = star_count (always 26); byte[7] = sim_steps;
        # num_players encoded indirectly — count active player slots.
        # Player records start at offset 17142, stride 63 bytes.
        OFFSET_PLAYER = 17142
        PLAYER_STRIDE = 63   # 9 name + 27*uint16 attrs = 9+54 = 63
        PLAYER_SLOTS  = 10
        OFFSET_ACTIVE_FLAG = 9   # attrs[0] = active_flag (uint16) at +9

        if len(data) < OFFSET_PLAYER + PLAYER_SLOTS * PLAYER_STRIDE:
            return 0, []

        names = []
        for i in range(PLAYER_SLOTS):
            off  = OFFSET_PLAYER + i * PLAYER_STRIDE
            name = data[off:off + 9].split(b'\x00')[0].decode('latin-1', errors='replace').strip()
            flag = struct.unpack_from('<H', data, off + OFFSET_ACTIVE_FLAG)[0]
            if flag != 101 and name:
                names.append(name)
        return len(names), names
    except Exception:
        return 0, []


class ScenarioDialog(BaseDialog):
    """Pick a scenario file to load."""

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen, "Load Scenario", width=480, height=360)
        self._paths    = _find_scenarios()
        self._meta     = [_quick_meta(p) for p in self._paths]
        self._selected = 0
        self._scroll   = 0
        self._btn_load:   pygame.Rect | None = None
        self._btn_cancel: pygame.Rect | None = None
        self._hover_load   = False
        self._hover_cancel = False

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self._hover_load   = self._btn_load   and self._btn_load.collidepoint(event.pos)
            self._hover_cancel = self._btn_cancel and self._btn_cancel.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_cancel and self._btn_cancel.collidepoint(pos):
                self.close(None); return
            if self._btn_load and self._btn_load.collidepoint(pos):
                self._confirm(); return
            # Row click
            cr = self._content_rect()
            row_top = cr.y + _ROW_H + 4 + _ROW_H   # after title + header row
            for ri in range(self._visible()):
                idx = self._scroll + ri
                if idx >= len(self._paths):
                    break
                r = pygame.Rect(cr.x, row_top + ri * _ROW_H, cr.width, _ROW_H)
                if r.collidepoint(pos):
                    self._selected = idx

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._selected = max(0, self._selected - 1)
                self._clamp_scroll()
            elif event.key == pygame.K_DOWN:
                self._selected = min(len(self._paths) - 1, self._selected + 1)
                self._clamp_scroll()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm()
            elif event.key == pygame.K_ESCAPE:
                self.close(None)

        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, min(
                max(0, len(self._paths) - self._visible()),
                self._scroll - event.y))

    def _visible(self):
        cr = self._content_rect()
        return max(1, (cr.height - _ROW_H * 2 - 54) // _ROW_H)

    def _clamp_scroll(self):
        vis = self._visible()
        if self._selected < self._scroll:
            self._scroll = self._selected
        elif self._selected >= self._scroll + vis:
            self._scroll = self._selected - vis + 1

    def _confirm(self):
        if self._paths and 0 <= self._selected < len(self._paths):
            self.close(self._paths[self._selected])

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        if not self._paths:
            surface.blit(self._text("No scenario files found.", (180, 100, 100)), (x, y))
            surface.blit(self._text(
                "Place SCWSCEN.A/D/I alongside the game or in a 'scenarios/' folder.",
                (140, 140, 160)), (x, y + _ROW_H + 4))
        else:
            surface.blit(self._text(f"{len(self._paths)} scenario(s) found", TITLE_COL), (x, y))
            y += _ROW_H + 4

            # Header
            for col_x, hdr in [(0, "File"), (120, "Players"), (200, "Factions")]:
                surface.blit(self._text(hdr, _HDR_COL), (x + col_x, y))
            y += _ROW_H

            vis = self._visible()
            for ri in range(vis):
                idx = self._scroll + ri
                if idx >= len(self._paths):
                    break
                path = self._paths[idx]
                num_p, names = self._meta[idx]
                fname = os.path.basename(path)
                names_str = ', '.join(names[:4])
                if len(names) > 4:
                    names_str += f' +{len(names)-4}'

                row_rect = pygame.Rect(cr.x, y, cr.width, _ROW_H)
                if idx == self._selected:
                    pygame.draw.rect(surface, _SEL_COL, row_rect)
                elif ri % 2 == 1:
                    pygame.draw.rect(surface, _ALT_COL, row_rect)

                surface.blit(self._text(fname), (x, y))
                surface.blit(self._text(str(num_p) if num_p else '?'), (x + 120, y))
                surface.blit(self._text(names_str, (180, 200, 180)), (x + 200, y))
                y += _ROW_H

        btn_y = self.rect.bottom - 42
        mid   = self.rect.centerx
        self._btn_cancel = pygame.Rect(mid - 110, btn_y, 100, 28)
        self._btn_load   = pygame.Rect(mid +  10, btn_y, 100, 28)
        self._draw_button(surface, self._btn_cancel, "Cancel", self._hover_cancel)
        load_label = "Load" if self._paths else "OK"
        self._draw_button(surface, self._btn_load, load_label,
                          self._hover_load and bool(self._paths))