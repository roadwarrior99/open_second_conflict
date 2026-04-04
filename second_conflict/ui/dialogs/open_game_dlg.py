"""Open Save Game dialog.

Shows a scrollable list of .sav files found in the working directory.
Clicking a file loads a quick preview (turn, players, difficulty).
Double-clicking or pressing Enter confirms the selection.
"""
import os
import glob
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.constants import EMPIRE_FACTION

_ROW_H      = 20
_LIST_W     = 220
_PREVIEW_X  = _LIST_W + 20   # x offset of preview panel within content rect
_HDR_COL    = (150, 150, 200)
_SEL_COL    = (40, 60, 110)
_DIM_COL    = (100, 100, 120)
_GOOD_COL   = (100, 200, 130)
_DIFFICULTY = {0: "Novice", 1: "Easy", 2: "Standard", 3: "Hard", 4: "Expert"}


class OpenGameDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, search_dir: str = '.'):
        super().__init__(screen, "Open Save Game", width=560, height=400)
        self._search_dir  = os.path.abspath(search_dir)
        self._files       = self._scan()
        self._selected    = 0
        self._scroll      = 0
        self._preview     = None   # cached parse result for selected file
        self._preview_err = ''
        self._hover_open  = False
        self._hover_can   = False
        self._btn_open    = None
        self._btn_can     = None
        self._row_rects: list[pygame.Rect] = []
        self._last_click  = (-1, 0)   # (index, ticks) for double-click detection

        if self._files:
            self._load_preview(0)

    # ------------------------------------------------------------------

    def _scan(self) -> list[dict]:
        """Return list of dicts with 'path', 'name', 'mtime' sorted newest-first."""
        pattern = os.path.join(self._search_dir, '*.sav')
        paths   = glob.glob(pattern)
        entries = []
        for p in paths:
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                mtime = 0
            entries.append({'path': p, 'name': os.path.basename(p), 'mtime': mtime})
        entries.sort(key=lambda e: e['mtime'], reverse=True)
        return entries

    def _load_preview(self, idx: int):
        self._preview     = None
        self._preview_err = ''
        if idx < 0 or idx >= len(self._files):
            return
        path = self._files[idx]['path']
        try:
            from second_conflict.io.scenario_parser import parse_file
            state = parse_file(path)
            self._preview = state
        except Exception as e:
            self._preview_err = str(e)[:60]

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self._hover_open = bool(self._btn_open and
                                    self._btn_open.collidepoint(event.pos))
            self._hover_can  = bool(self._btn_can  and
                                    self._btn_can.collidepoint(event.pos))

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            if event.button == 1:
                if self._btn_open and self._btn_open.collidepoint(pos):
                    self._confirm(); return
                if self._btn_can  and self._btn_can.collidepoint(pos):
                    self.close(None); return
                for i, r in enumerate(self._row_rects):
                    if r.collidepoint(pos):
                        if i != self._selected:
                            self._selected = i
                            self._scroll   = min(self._scroll,
                                                 max(0, i - self._visible_count() + 1))
                            self._load_preview(i)
                        else:
                            # Double-click check
                            now = pygame.time.get_ticks()
                            prev_idx, prev_t = self._last_click
                            if prev_idx == i and now - prev_t < 400:
                                self._confirm(); return
                        self._last_click = (i, pygame.time.get_ticks())
                        return
            elif event.button == 4:
                self._scroll = max(0, self._scroll - 1)
            elif event.button == 5:
                self._scroll = min(self._scroll + 1,
                                   max(0, len(self._files) - self._visible_count()))

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and self._selected > 0:
                self._selected -= 1
                self._scroll = min(self._scroll, self._selected)
                self._load_preview(self._selected)
            elif event.key == pygame.K_DOWN and self._selected < len(self._files) - 1:
                self._selected += 1
                if self._selected >= self._scroll + self._visible_count():
                    self._scroll = self._selected - self._visible_count() + 1
                self._load_preview(self._selected)
            elif event.key == pygame.K_RETURN:
                self._confirm()

    def _confirm(self):
        if self._files and self._selected < len(self._files):
            self.close(self._files[self._selected]['path'])
        else:
            self.close(None)

    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        # ---- File list (left) ----
        surface.blit(self._font_body.render("Save files", True, _HDR_COL), (x, y))
        pygame.draw.line(surface, (60, 60, 90),
                         (x, y + _ROW_H - 2), (x + _LIST_W, y + _ROW_H - 2))

        self._row_rects = []
        vis   = self._visible_count()
        ry    = y + _ROW_H
        for vi in range(vis):
            fi = self._scroll + vi
            if fi >= len(self._files):
                break
            entry = self._files[fi]
            r = pygame.Rect(x, ry, _LIST_W, _ROW_H)
            self._row_rects.append(r)
            if fi == self._selected:
                pygame.draw.rect(surface, _SEL_COL, r)
            name = entry['name']
            if len(name) > 22:
                name = name[:19] + '...'
            surface.blit(self._font_body.render(name, True, TEXT_COL), (x + 4, ry + 2))
            ry += _ROW_H

        if not self._files:
            surface.blit(self._font_body.render("No .sav files found.", True, _DIM_COL),
                         (x + 4, y + _ROW_H + 4))

        # Divider between list and preview
        px = cr.x + _PREVIEW_X
        pygame.draw.line(surface, (60, 60, 90),
                         (px - 8, y), (px - 8, cr.bottom))

        # ---- Preview panel (right) ----
        surface.blit(self._font_body.render("Preview", True, _HDR_COL), (px, y))
        pygame.draw.line(surface, (60, 60, 90),
                         (px, y + _ROW_H - 2), (cr.right, y + _ROW_H - 2))
        py = y + _ROW_H

        if self._preview_err:
            surface.blit(self._font_body.render("Error loading file:", True, (220, 80, 80)),
                         (px, py)); py += _ROW_H
            surface.blit(self._font_body.render(self._preview_err, True, _DIM_COL),
                         (px, py))
        elif self._preview:
            s = self._preview
            opts = s.options

            def row(label, value, col=TEXT_COL):
                nonlocal py
                surface.blit(self._font_body.render(f"{label}:", True, _HDR_COL), (px, py))
                surface.blit(self._font_body.render(str(value), True, col), (px + 90, py))
                py += _ROW_H

            row("Turn",       s.turn)
            row("Map size",   opts.map_param)
            row("Difficulty", _DIFFICULTY.get(opts.difficulty, str(opts.difficulty)))
            row("Sim steps",  opts.sim_steps)

            py += 4
            surface.blit(self._font_body.render("Players", True, _HDR_COL), (px, py))
            py += _ROW_H

            for p in s.players:
                if not p.is_active:
                    continue
                if p.faction_id == EMPIRE_FACTION:
                    continue
                kind = "AI" if not p.is_human else "Human"
                stars = sum(1 for st in s.stars
                            if st.owner_faction_id == p.faction_id)
                line = f"  {p.name[:16]:<16}  {kind:<5}  {stars} stars"
                surface.blit(self._font_body.render(line, True, _GOOD_COL), (px, py))
                py += _ROW_H
        elif self._files:
            surface.blit(self._font_body.render("Select a file to preview.",
                                                 True, _DIM_COL), (px, py))

        # ---- Buttons ----
        btn_y = self.rect.bottom - 38
        self._btn_open = pygame.Rect(self.rect.centerx - 100, btn_y, 80, 28)
        self._btn_can  = pygame.Rect(self.rect.centerx + 20,  btn_y, 80, 28)
        can_open = bool(self._files and self._preview)
        self._draw_button(surface, self._btn_open, "Open",   self._hover_open and can_open)
        self._draw_button(surface, self._btn_can,  "Cancel", self._hover_can)

    def _visible_count(self) -> int:
        cr = self._content_rect()
        return max(1, (cr.height - _ROW_H - 40) // _ROW_H)