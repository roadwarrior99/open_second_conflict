"""Events / news ticker dialog.

Shows the list of EventEntry messages for the current player after
end-of-turn processing.  Matches SCOUTVIEWDLG / REINFVIEWDLG / REVOLTVIEWDLG
behaviour: paginated list, OK to dismiss.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL
from second_conflict.model.game_state import EventEntry

_LINE_H    = 18
_DIALOG_W  = 560
_BADGE_W   = 76
_TEXT_W    = _DIALOG_W - 20 - _BADGE_W   # usable width for message text
_VISIBLE   = 16

_CATEGORY_COLOURS = {
    'scout':    (100, 200, 255),
    'reinforce':(100, 255, 160),
    'revolt':   (255, 160, 80),
    'combat':   (255, 80,  80),
    'event':    (200, 200, 200),
}


def _wrap(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    """Word-wrap *text* to fit within *max_w* pixels. Returns list of lines."""
    words = text.split()
    lines: list[str] = []
    current = ''
    for word in words:
        candidate = (current + ' ' + word).strip()
        if font.size(candidate)[0] <= max_w:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ['']


class EventsDialog(BaseDialog):
    """Show a list of EventEntry objects to the player."""

    def __init__(self, screen: pygame.Surface, entries: list[EventEntry]):
        # Pre-wrap all entries into display lines so we can size the dialog.
        # Each entry produces (category, line_text) tuples; the category is
        # only set on the first line of each entry.
        font = pygame.font.SysFont('monospace', 13)
        self._lines: list[tuple[str, str]] = []
        for entry in entries:
            wrapped = _wrap(entry.text, font, _TEXT_W)
            for i, line in enumerate(wrapped):
                self._lines.append((entry.category if i == 0 else '', line))

        visible = min(len(self._lines), _VISIBLE)
        height  = 60 + visible * _LINE_H + 50
        super().__init__(screen, "Dispatches", width=_DIALOG_W, height=max(height, 180))
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
                self._scroll = min(self._scroll + 1,
                                   max(0, len(self._lines) - _VISIBLE))
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.close(None)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        if not self._lines:
            surface.blit(self._text("No dispatches this turn."), (x, y))
        else:
            for category, line_text in self._lines[self._scroll: self._scroll + _VISIBLE]:
                if category:
                    cat_col = _CATEGORY_COLOURS.get(category, TEXT_COL)
                    badge = self._font_body.render(
                        f"[{category[:5]:5}]", True, cat_col)
                    surface.blit(badge, (x, y))
                surface.blit(self._text(line_text), (x + _BADGE_W, y))
                y += _LINE_H

            # Scroll indicator
            if len(self._lines) > _VISIBLE:
                note = self._text(
                    f"  {self._scroll + 1}–{min(self._scroll + _VISIBLE, len(self._lines))} "
                    f"of {len(self._lines)} lines  (scroll with mouse wheel)",
                    (120, 120, 140)
                )
                surface.blit(note, (x, y))

        # OK button
        btn_y = self.rect.bottom - 40
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)