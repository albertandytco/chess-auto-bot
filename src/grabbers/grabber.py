from abc import ABC, abstractmethod
from selenium.webdriver.remote.webdriver import WebDriver

from utilities import attach_to_session


class Grabber(ABC):
    """
    Abstract base class for interacting with different chess websites.

    This class provides a common interface for performing actions on chess
    websites like chess.com and lichess.org. Subclasses must implement the
    abstract methods defined here to provide site-specific behavior.
    """

    def __init__(self, chrome_url, chrome_session_id):
        """
        Initializes the Grabber with a WebDriver instance.

        Args:
            chrome_url (str): The URL of the ChromeDriver.
            chrome_session_id (str): The ID of the Chrome session.
        """
        self.chrome: WebDriver = attach_to_session(chrome_url, chrome_session_id)
        self._board_elem = None

    def get_board(self):
        """
        Returns the board element.

        Returns:
            WebElement: The board element.
        """
        return self._board_elem

    def get_top_left_corner(self):
        """
        Gets the coordinates of the top-left corner of the browser window.

        Returns:
            tuple: A tuple containing the x and y coordinates of the top-left corner.
        """
        canvas_x_offset = self.chrome.execute_script(
            "return window.screenX + (window.outerWidth - window.innerWidth) / 2 - window.scrollX;"
        )
        canvas_y_offset = self.chrome.execute_script(
            "return window.screenY + (window.outerHeight - window.innerHeight) - window.scrollY;"
        )
        return canvas_x_offset, canvas_y_offset

    @abstractmethod
    def update_board_elem(self):
        """
        Updates the internal representation of the board element.

        This method should find and store the board element on the page.
        """
        pass

    @abstractmethod
    def is_white(self):
        """
        Determines if the player is playing as white.

        Returns:
            bool: True if the player is white, False if black, None if unknown.
        """
        pass

    @abstractmethod
    def is_game_over(self):
        """
        Checks if the game is over.

        Returns:
            bool: True if the game is over, False otherwise.
        """
        pass

    @abstractmethod
    def get_move_list(self):
        """
        Gets the list of moves from the game.

        Returns:
            list: A list of moves, e.g., ["e4", "c5", "Nf3"].
        """
        pass

    @abstractmethod
    def is_game_puzzles(self):
        """
        Checks if the current game is a puzzle.

        Returns:
            bool: True if it's a puzzle, False otherwise.
        """
        pass

    @abstractmethod
    def click_puzzle_next(self):
        """
        Clicks the "next puzzle" button.
        """
        pass

    @abstractmethod
    def make_mouseless_move(self, move, move_count):
        """
        Makes a move without moving the mouse.
        Args:
             move (string): The move in uci format.
             move_count (int): The move count.
        """
        pass

    def close_chrome(self):
        """
        Closes the chrome browser.
        """
        self.chrome.quit()
