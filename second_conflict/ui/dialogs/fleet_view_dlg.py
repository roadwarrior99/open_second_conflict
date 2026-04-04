"""Fleet view dialog — translation of FLEETVIEWDLG from SCW.EXE.

Shows a scrollable list of all your active in-transit fleets.
Columns: Slot#, Dest, Turns, War, Troop, Stlth, Msle, Scout, Probe, Type
  Troop = troops embarked on this fleet's TranSports (not transport count).
Selecting an entry and clicking OK jumps the map to that fleet's destination.
Returns the selected dest_star index or None.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.constants import FREE_SLOT
from second_conflict.model.game_state import GameState

_ROW_H = 18
_HDR_COLS = ["Owner",  "Dest", "Turns", "War", "Troop", "Stlth", "Msle", "Scout", "Probe", "Type"]
_COL_XS   = [0,        110,    150,     195,   235,     280,     325,    365,     405,     440]


class FleetViewDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, state: GameState,
                 player_faction: int):
        super().__init__(screen, "Fleet Status", width=620, height=380)
        self.state          = state
        self.player_faction = player_faction
        self._dev_mode      = state.options.dev_mode

        # In dev mode show ALL active fleets, not just the current player's
        if self._dev_mode:
            self._fleets = [
                (i, f) for i, f in enumerate(state.fleets_in_transit)
                if not f.is_free
            ]
        else:
            self._fleets = [
                (i, f) for i, f in enumerate(state.fleets_in_transit)
                if f.owner_faction_id == player_faction
            ]
        self._selected     = 0
        self._scroll       = 0
        self._hover_ok     = False
        self._hover_can    = False
        self._hover_recall = False
        self._hover_edit   = False
        self._btn_ok       = None
        self._btn_can      = None
        self._btn_recall   = None
        self._btn_edit     = None
        self._recall_msg   = ""

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        visible = self._visible_count()
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok     = self._btn_ok     and self._btn_ok.collidepoint(event.pos)
            self._hover_can    = self._btn_can    and self._btn_can.collidepoint(event.pos)
            self._hover_recall = self._btn_recall and self._btn_recall.collidepoint(event.pos)
            self._hover_edit   = self._btn_edit   and self._btn_edit.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self._btn_ok  and self._btn_ok.collidepoint(event.pos):
                    self._confirm()
                    return
                if self._btn_can and self._btn_can.collidepoint(event.pos):
                    self.close(None)
                    return
                if self._btn_recall and self._btn_recall.collidepoint(event.pos):
                    self._do_recall()
                    return
                if self._btn_edit and self._btn_edit.collidepoint(event.pos):
                    self._do_edit()
                    return
                # Row click
                cr = self._content_rect()
                row_y = cr.y + _ROW_H + 2  # after header row + 2px divider line
                for vi in range(visible):
                    fi = self._scroll + vi
                    if fi >= len(self._fleets):
                        break
                    rect = pygame.Rect(cr.x, row_y + vi * _ROW_H, cr.width, _ROW_H)
                    if rect.collidepoint(event.pos):
                        self._selected = fi
            elif event.button == 4:
                self._scroll = max(0, self._scroll - 1)
            elif event.button == 5:
                self._scroll = min(max(0, len(self._fleets) - visible), self._scroll + 1)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._selected = max(0, self._selected - 1)
                self._scroll   = min(self._scroll, self._selected)
            elif event.key == pygame.K_DOWN:
                self._selected = min(len(self._fleets) - 1, self._selected + 1)
                if self._selected >= self._scroll + visible:
                    self._scroll = self._selected - visible + 1
            elif event.key == pygame.K_RETURN:
                self._confirm()

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        if not self._fleets:
            surface.blit(self._text("No fleets in transit."), (x, y))
        else:
            # Header
            for col, hdr in zip(_COL_XS, _HDR_COLS):
                s = self._font_body.render(hdr, True, (150, 150, 200))
                surface.blit(s, (x + col, y))
            y += _ROW_H
            pygame.draw.line(surface, (60, 60, 90), (x, y), (x + cr.width, y))
            y += 2

            visible = self._visible_count()
            for vi in range(visible):
                fi = self._scroll + vi
                if fi >= len(self._fleets):
                    break
                slot_idx, fleet = self._fleets[fi]
                row_rect = pygame.Rect(x, y, cr.width, _ROW_H)
                if fi == self._selected:
                    pygame.draw.rect(surface, (40, 60, 100), row_rect)
                owner = self.state.player_for_faction(fleet.owner_faction_id)
                owner_name = owner.name[:13] if owner else f"0x{fleet.owner_faction_id:02x}"
                cols = [
                    owner_name,
                    str(fleet.dest_star),
                    str(fleet.turns_remaining),
                    str(fleet.warships),
                    str(fleet.troop_ships),
                    str(fleet.stealthships),
                    str(fleet.missiles),
                    str(fleet.scouts),
                    str(fleet.probes),
                    fleet.fleet_type_char,
                ]
                for col_x, text in zip(_COL_XS, cols):
                    s = self._text(text)
                    surface.blit(s, (x + col_x, y))
                y += _ROW_H

            # Scroll indicator
            if len(self._fleets) > visible:
                note = self._text(
                    f"  {self._scroll+1}-{min(self._scroll+visible, len(self._fleets))} "
                    f"of {len(self._fleets)}",
                    (120, 120, 140)
                )
                surface.blit(note, (x, y))

        # Totals / recall feedback line
        if self._recall_msg:
            bottom_text = self._text(self._recall_msg, (180, 220, 180))
        else:
            total_w = sum(f.warships    for _, f in self._fleets)
            total_t = sum(f.troop_ships for _, f in self._fleets)
            total_s = sum(f.scouts      for _, f in self._fleets)
            bottom_text = self._text(
                f"Totals — W:{total_w}  T:{total_t}  S:{total_s}",
                (160, 200, 160)
            )
        surface.blit(bottom_text, (cr.x, self.rect.bottom - 60))

        # Buttons
        btn_y = self.rect.bottom - 38
        if self._dev_mode:
            self._btn_ok     = pygame.Rect(self.rect.centerx - 190, btn_y, 70, 28)
            self._btn_recall = pygame.Rect(self.rect.centerx - 110, btn_y, 80, 28)
            self._btn_edit   = pygame.Rect(self.rect.centerx - 20,  btn_y, 60, 28)
            self._btn_can    = pygame.Rect(self.rect.centerx + 50,  btn_y, 70, 28)
            self._draw_button(surface, self._btn_ok,     "Go To",  self._hover_ok)
            self._draw_button(surface, self._btn_recall, "Recall", self._hover_recall)
            # Amber "Edit" button — draw manually to distinguish from normal buttons
            edit_col = (200, 160, 40) if self._hover_edit else (140, 100, 20)
            pygame.draw.rect(surface, edit_col, self._btn_edit, border_radius=4)
            lbl = self._font_body.render("Edit", True, (255, 255, 255))
            surface.blit(lbl, (self._btn_edit.centerx - lbl.get_width() // 2,
                               self._btn_edit.centery - lbl.get_height() // 2))
            self._draw_button(surface, self._btn_can,    "Close",  self._hover_can)
        else:
            self._btn_edit   = None
            self._btn_ok     = pygame.Rect(self.rect.centerx - 150, btn_y, 80, 28)
            self._btn_recall = pygame.Rect(self.rect.centerx - 60,  btn_y, 90, 28)
            self._btn_can    = pygame.Rect(self.rect.centerx + 40,  btn_y, 80, 28)
            self._draw_button(surface, self._btn_ok,     "Go To",  self._hover_ok)
            self._draw_button(surface, self._btn_recall, "Recall", self._hover_recall)
            self._draw_button(surface, self._btn_can,    "Close",  self._hover_can)

    # ------------------------------------------------------------------

    def _confirm(self):
        if self._fleets and self._selected < len(self._fleets):
            _, fleet = self._fleets[self._selected]
            self.close(fleet.dest_star)
        else:
            self.close(None)

    def _do_edit(self):
        if not self._dev_mode or not self._fleets or self._selected >= len(self._fleets):
            return
        from second_conflict.ui.dialogs.fleet_editor_dlg import FleetEditorDialog
        _, fleet = self._fleets[self._selected]
        FleetEditorDialog(self.screen, fleet, self.state).run()
        self._recall_msg = f"Fleet slot {fleet.slot} updated."

    def _do_recall(self):
        if not self._fleets or self._selected >= len(self._fleets):
            return
        from second_conflict.engine.fleet_transit import recall_fleet
        _, fleet = self._fleets[self._selected]
        ok = recall_fleet(self.state, fleet)
        if ok:
            self._recall_msg = (f"Fleet recalled — now heading to star {fleet.dest_star} "
                                f"({fleet.turns_remaining} turns)")
        else:
            self._recall_msg = "Missiles cannot be recalled."

    def _visible_count(self) -> int:
        cr = self._content_rect()
        available_h = cr.height - _ROW_H * 2 - 60  # subtract header + totals + buttons
        return max(1, available_h // _ROW_H)