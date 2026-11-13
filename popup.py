"""Right-click menus of the cats that close when clicking elsewhere.

The cats are X11 windows (XWayland under Wayland) that never take the focus,
so as not to steal the keyboard. A Qt menu closes on a click outside only when
it can grab the pointer, and that grab fails while the program has no focus:
the click went to the window underneath and the menu stayed open.

While the menu is open, an invisible window covers the screens, under the
menu: a click on it closes the menu, as a click outside a menu does anywhere.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QGuiApplication, QPainter
from PyQt6.QtWidgets import QWidget


class _Catcher(QWidget):
    """Invisible window over every screen; any click closes the menu."""

    def __init__(self, menu):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.X11BypassWindowManagerHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.Tool,
        )
        self.menu = menu
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(QGuiApplication.primaryScreen().virtualGeometry())

    def paintEvent(self, _event):
        # Almost transparent rather than transparent: the window must be drawn
        # to receive the clicks.
        QPainter(self).fillRect(self.rect(), QColor(0, 0, 0, 1))

    def mousePressEvent(self, _event):
        self.menu.close()


def show_menu(menu, position):
    """menu.exec(position), closed by a click anywhere outside the menu."""
    catcher = _Catcher(menu)
    catcher.show()  # shown first: the menu opens above it
    try:
        return menu.exec(position)
    finally:
        catcher.close()
        catcher.deleteLater()
