import math
import sys
import threading
import time

from PyQt6.QtCore import Qt, QPoint, QThread
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QGuiApplication, QPolygon
from PyQt6.QtWidgets import QApplication, QWidget

# Constants for colors and arrow size
ARROW_COLOR = QColor(255, 0, 0, 122)  # Semi-transparent red
ARROW_HEIGHT = 25


class OverlayScreen(QWidget):
    """
    Overlay widget to display arrows on the screen, indicating suggested chess moves.
    """

    def __init__(self, stockfish_queue):
        """
        Initializes the OverlayScreen.

        Args:
            stockfish_queue (multiprocessing.Queue): The queue to receive move data from Stockfish.
        """
        super().__init__()
        self.stockfish_queue = stockfish_queue

        # Set the window to be the size of the screen
        self.screen = QGuiApplication.screens()[0]
        self.setFixedWidth(self.screen.size().width())
        self.setFixedHeight(self.screen.size().height())

        # Set the window to be transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        # A list of QPolygon objects containing the points of the arrows
        self.arrows = []

        # Start the message queue thread
        self.message_queue_thread = threading.Thread(target=self.message_queue_thread, daemon=True)
        self.exit_event = threading.Event()
        self.message_queue_thread.start()

    def message_queue_thread(self):
        """Receives messages from the stockfish queue and updates the arrows."""
        while not self.exit_event.is_set():
            try:
                if not self.stockfish_queue.empty():
                    message = self.stockfish_queue.get()
                    self.set_arrows(message)
                else:
                    time.sleep(0.1)

            except Exception as e:
                print(f"Error in message_queue_thread: {e}")

    def set_arrows(self, arrows):
        """Sets the arrows to be drawn on the screen.

        Args:
            arrows (list): A list of tuples, each containing the start and end position
                           of an arrow in the form ((start_x, start_y), (end_x, end_y)).
        """
        self.arrows = []
        for arrow in arrows:
            poly = self.get_arrow_polygon(
                QPoint(arrow[0][0], arrow[0][1]),
                QPoint(arrow[1][0], arrow[1][1]),
            )
            self.arrows.append(poly)
        self.update()

    def closeEvent(self, event):
        """
        Override the close event.
        """
        self.exit_event.set()
        self.message_queue_thread.join()
        event.accept()

    def paintEvent(self, event):
        """Draws the arrows on the screen."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.red, 1, Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(ARROW_COLOR, Qt.BrushStyle.SolidPattern))
        for arrow in self.arrows:
            painter.drawPolygon(arrow)
        painter.end()

    def get_arrow_polygon(self, start_point, end_point):
        """Calculates the polygon for drawing an arrow.

        Args:
            start_point (QPoint): The starting point of the arrow.
            end_point (QPoint): The ending point of the arrow.

        Returns:
            QPolygon: A polygon representing the arrow.
        """
        try:
            # Calculate the vector from start to end
            dx, dy = start_point.x() - end_point.x(), start_point.y() - end_point.y()

            # Normalize the vector
            leng = math.sqrt(dx ** 2 + dy ** 2)
            if leng == 0:
                return QPolygon([start_point, end_point])
            norm_x, norm_y = dx / leng, dy / leng  # Normalized direction vector

            # Perpendicular vector to the direction vector
            perp_x, perp_y = -norm_y, norm_x

            # Define arrow head and base points
            # left base
            left_x = (
                end_point.x() + ARROW_HEIGHT * norm_x * 1.5 + ARROW_HEIGHT * perp_x
            )
            left_y = (
                end_point.y() + ARROW_HEIGHT * norm_y * 1.5 + ARROW_HEIGHT * perp_y
            )
            # right base
            right_x = (
                end_point.x() + ARROW_HEIGHT * norm_x * 1.5 - ARROW_HEIGHT * perp_x
            )
            right_y = (
                end_point.y() + ARROW_HEIGHT * norm_y * 1.5 - ARROW_HEIGHT * perp_y
            )
            # start left and right
            start_left = QPoint(
                int(start_point.x() + (ARROW_HEIGHT / 5) * perp_x),
                int(start_point.y() + (ARROW_HEIGHT / 5) * perp_y),
            )
            start_right = QPoint(
                int(start_point.x() - (ARROW_HEIGHT / 5) * perp_x),
                int(start_point.y() - (ARROW_HEIGHT / 5) * perp_y),
            )

            point2 = QPoint(int(left_x), int(left_y))
            point3 = QPoint(int(right_x), int(right_y))

            mid_point1 = QPoint(int((2 / 5) * point2.x() + (3 / 5) * point3.x()), int((2 / 5) * point2.y() + (3 / 5) * point3.y()))
            mid_point2 = QPoint(int((3 / 5) * point2.x() + (2 / 5) * point3.x()), int((3 / 5) * point2.y() + (2 / 5) * point3.y()))

            return QPolygon([end_point, point2, mid_point1, start_right, start_left, mid_point2, point3])
        except Exception as e:
            print(f"Error in get_arrow_polygon: {e}")
            return QPolygon([start_point, end_point])


def run(stockfish_queue):
    """Runs the overlay application.

    Initializes the PyQt application, creates an OverlayScreen instance,
    and starts the main event loop.

    The overlay displays arrows on the screen based on data received
    from the stockfish_queue.

    Args:
        stockfish_queue: The message queue used to communicate with the stockfish thread
    Returns:
        None
    """

    app = QApplication(sys.argv)
    overlay = OverlayScreen(stockfish_queue)
    overlay.show()
    sys.exit(app.exec())
