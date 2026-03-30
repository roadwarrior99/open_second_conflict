"""Events / news ticker dialog.

Shows the list of EventEntry messages for the current player after
end-of-turn processing.  Matches SCOUTVIEWDLG / REINFVIEWDLG / REVOLTVIEWDLG
behaviour: paginated list, OK to dismiss.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL
from second_conflict.model.game_state import EventEntry

_LINE_H   = 18
_CATEGORY_COLOURS = {
    'scout':    (100, 200, 255),
    'reinforce':(100, 255, 160),
    'revolt':   (255, 160, 80),
    'combat':   (255, 80,  80),
    'event':    (200, 200, 200),
}


class EventsDialog(BaseDialog):
    """Show a list of EventEntry objects to the player."""

    def __init__(self, screen: pygame.Surface, entries: list[EventEntry]):
        # Size dynamically to content (capped)
        visible = min(len(entries), 16)
        height  = 60 + visible * _LINE_H + 50
        super().__init__(screen, "Dispatches", width=520, height=max(height, 180))
        self._entries   = entries
        self._scroll    = 0
        self._hover_ok  = False
        self._btn_ok    = None

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok = self._btn_ok and self._btn_ok.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self._btn_ok and self._btn_ok.collidepoint(event.pos):
                self.close(None)
            elif event.button == 4:   # scroll up
                self._scroll = max(0, self._scroll - 1)
            elif event.button == 5:   # scroll down
                max_scroll = max(0, len(self._entries) - 16)
                self._scroll = min(self._scroll + 1, max_scroll)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.close(None)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        if not self._entries:
            surface.blit(self._text("No dispatches this turn."), (x, y))
        else:
            visible_entries = self._entries[self._scroll: self._scroll + 16]
            for entry in visible_entries:
                cat_col = _CATEGORY_COLOURS.get(entry.category, TEXT_COL)
                # Category badge
                badge = self._font_body.render(f"[{entry.category[:5]:5}]", True, cat_col)
                surface.blit(badge, (x, y))
                # Message (truncated to fit)
                msg = entry.text
                if len(msg) > 54:
                    msg = msg[:51] + "..."
                text_surf = self._text(msg)
                surface.blit(text_surf, (x + 76, y))
                y += _LINE_H

            # Scroll indicator
            if len(self._entries) > 16:
                note = self._text(
                    f"  {self._scroll+1}-{min(self._scroll+16, len(self._entries))} "
                    f"of {len(self._entries)}  (scroll with mouse wheel)",
                    (120, 120, 140)
                )
                surface.blit(note, (x, y))
                y += _LINE_H

        # OK button
        btn_y = self.rect.bottom - 40
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)