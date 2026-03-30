"""Modal dialog base class.

All dialogs inherit from this.  A dialog renders on top of the map using
a semi-transparent backdrop.  It handles its own event loop when shown
modally via .run().
"""
import pygame

DIALOG_BG     = (25, 30, 45)
DIALOG_BORDER = (80, 100, 160)
TITLE_COL     = (220, 220, 255)
TEXT_COL      = (200, 200, 200)
BTN_NORMAL    = (50, 80, 140)
BTN_HOVER     = (80, 120, 200)
BTN_TEXT_COL  = (255, 255, 255)
BACKDROP_COL  = (0, 0, 0, 160)   # RGBA

_FONT_TITLE_SIZE = 16
_FONT_BODY_SIZE  = 13


class BaseDialog:
    def __init__(self, screen: pygame.Surface, title: str,
                 width: int = 400, height: int = 300):
        self.screen = screen
        self.title  = title
        self.width  = width
        self.height = height

        sw, sh = screen.get_size()
        self.rect = pygame.Rect(
            (sw - width) // 2,
            (sh - height) // 2,
            width, height,
        )
        self._font_title = pygame.font.SysFont('monospace', _FONT_TITLE_SIZE, bold=True)
        self._font_body  = pygame.font.SysFont('monospace', _FONT_BODY_SIZE)
        self._result     = None   # filled in by subclass before close()
        self._running    = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> object:
        """Block until the dialog is dismissed.  Returns self._result."""
        self._running = True
        clock = pygame.time.Clock()
        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    self._result = None
                self.handle_event(event)
            dt = clock.tick(30)
            self.update(dt)
            self._draw_backdrop()
            self.draw(self.screen)
            pygame.display.flip()
        return self._result

    def close(self, result=None):
        self._result  = result
        self._running = False

    # ------------------------------------------------------------------
    # Overridable hooks
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        """Override to handle input.  Call super() to get ESC-to-close."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close(None)

    def update(self, dt: int):
        """Called every frame with elapsed milliseconds.  Override for animations
        or hold-repeat button logic."""

    def draw(self, surface: pygame.Surface):
        """Override to draw dialog contents.  Call super() first."""
        # Dialog background
        pygame.draw.rect(surface, DIALOG_BG, self.rect, border_radius=6)
        pygame.draw.rect(surface, DIALOG_BORDER, self.rect, width=2, border_radius=6)
        # Title bar
        title_surf = self._font_title.render(self.title, True, TITLE_COL)
        surface.blit(title_surf, (self.rect.x + 10, self.rect.y + 8))
        # Divider below title
        dy = self.rect.y + 30
        pygame.draw.line(surface, DIALOG_BORDER,
                         (self.rect.x + 4, dy), (self.rect.right - 4, dy))

    # ------------------------------------------------------------------
    # Helpers for subclasses
    # ------------------------------------------------------------------

    def _content_rect(self) -> pygame.Rect:
        """Usable content area below the title bar."""
        return pygame.Rect(
            self.rect.x + 10,
            self.rect.y + 36,
            self.rect.width - 20,
            self.rect.height - 46,
        )

    def _draw_button(self, surface: pygame.Surface, rect: pygame.Rect,
                     label: str, hover: bool = False) -> None:
        col = BTN_HOVER if hover else BTN_NORMAL
        pygame.draw.rect(surface, col, rect, border_radius=4)
        lbl = self._font_body.render(label, True, BTN_TEXT_COL)
        surface.blit(lbl, (
            rect.centerx - lbl.get_width() // 2,
            rect.centery - lbl.get_height() // 2,
        ))

    def _draw_backdrop(self):
        """Draw a semi-transparent dark overlay over the whole screen."""
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill(BACKDROP_COL)
        self.screen.blit(overlay, (0, 0))

    def _text(self, text: str, colour=None) -> pygame.Surface:
        return self._font_body.render(text, True, colour or TEXT_COL)

    def _title_text(self, text: str, colour=None) -> pygame.Surface:
        return self._font_title.render(text, True, colour or TITLE_COL)