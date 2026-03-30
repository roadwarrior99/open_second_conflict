"""Inter-player message dialogs — translation of SCWPLRMSGDLG / SCWMESSAGEDLG.

SCWPLRMSGDLG: compose and send a short message to another player.
SCWMESSAGEDLG: display a received message (Yes/No confirmation variant).

Usage:
    # Send dialog
    result = SendMessageDialog(screen, state, from_player, to_player).run()
    # result is the message string, or None if cancelled.

    # Receive dialog
    result = ReceiveMessageDialog(screen, "Admiral X says: ...", title).run()
    # result is True (OK) or False (Cancel / No).
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL

_MAX_MSG_LEN = 80


class SendMessageDialog(BaseDialog):
    """Compose a short message to send to another player."""

    def __init__(self, screen: pygame.Surface, from_name: str, to_name: str):
        super().__init__(screen, f"Message to {to_name}", width=420, height=200)
        self._from_name = from_name
        self._to_name   = to_name
        self._text_buf  = ""
        self._hover_ok  = False
        self._hover_can = False
        self._btn_ok    = None
        self._btn_can   = None

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok  = self._btn_ok  and self._btn_ok.collidepoint(event.pos)
            self._hover_can = self._btn_can and self._btn_can.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_ok  and self._btn_ok.collidepoint(event.pos):
                self.close(self._text_buf or None)
            if self._btn_can and self._btn_can.collidepoint(event.pos):
                self.close(None)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.close(self._text_buf or None)
            elif event.key == pygame.K_BACKSPACE:
                self._text_buf = self._text_buf[:-1]
            elif event.unicode and len(self._text_buf) < _MAX_MSG_LEN:
                self._text_buf += event.unicode

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        prompt = self._text(f"From {self._from_name} to {self._to_name}:", TITLE_COL)
        surface.blit(prompt, (x, y)); y += 22

        # Text input box
        box = pygame.Rect(x, y, cr.width, 22)
        pygame.draw.rect(surface, (35, 40, 60), box)
        pygame.draw.rect(surface, (90, 90, 160), box, 1)
        inp = self._text(self._text_buf + "|")
        surface.blit(inp, (box.x + 4, box.y + 3))
        y += 32

        char_count = self._text(f"{len(self._text_buf)}/{_MAX_MSG_LEN}", (100, 100, 140))
        surface.blit(char_count, (x, y))

        btn_y = self.rect.bottom - 40
        self._btn_ok  = pygame.Rect(self.rect.centerx - 100, btn_y, 90, 28)
        self._btn_can = pygame.Rect(self.rect.centerx + 10,  btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok,  "Send",   self._hover_ok)
        self._draw_button(surface, self._btn_can, "Cancel", self._hover_can)


class ReceiveMessageDialog(BaseDialog):
    """Display a received message with an OK button (optionally Yes/No)."""

    def __init__(self, screen: pygame.Surface, message: str,
                 title: str = "Message", yes_no: bool = False):
        lines   = _wrap(message, 50)
        height  = 80 + 18 * len(lines) + 50
        super().__init__(screen, title, width=420, height=max(height, 160))
        self._lines     = lines
        self._yes_no    = yes_no
        self._hover_yes = False
        self._hover_no  = False
        self._btn_yes   = None
        self._btn_no    = None

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_yes = self._btn_yes and self._btn_yes.collidepoint(event.pos)
            self._hover_no  = self._btn_no  and self._btn_no.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_yes and self._btn_yes.collidepoint(event.pos):
                self.close(True)
            if self._btn_no  and self._btn_no.collidepoint(event.pos):
                self.close(False)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.close(True)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y
        for line in self._lines:
            surface.blit(self._text(line), (x, y))
            y += 18

        btn_y = self.rect.bottom - 40
        if self._yes_no:
            self._btn_yes = pygame.Rect(self.rect.centerx - 100, btn_y, 90, 28)
            self._btn_no  = pygame.Rect(self.rect.centerx + 10,  btn_y, 90, 28)
            self._draw_button(surface, self._btn_yes, "  Yes  ", self._hover_yes)
            self._draw_button(surface, self._btn_no,  "   No  ", self._hover_no)
        else:
            self._btn_yes = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
            self._btn_no  = None
            self._draw_button(surface, self._btn_yes, "   OK  ", self._hover_yes)


def _wrap(text: str, width: int) -> list[str]:
    """Simple word-wrap."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]