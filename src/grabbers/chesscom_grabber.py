from enum import Enum
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from grabbers.grabber import Grabber


# Constants for XPATH and CSS selectors
BOARD_PLAY_COMPUTER_XPATH = "//*[@id='board-play-computer']"
BOARD_SINGLE_XPATH = "//*[@id='board-single']"
COORDINATES_CLASS = "coordinates"
SQUARE_XPATH = ".//*"
MOVE_LIST_PLAY_CLASS = "play-controller-scrollable"
MOVE_LIST_SWAP_CLASS = "mode-swap-move-list-wrapper-component"
MOVE_NODE_SELECTOR = "div.node[data-node]"
FIGURINE_SELECTOR = "[data-figurine]"
GAME_OVER_WINDOW_CLASS = "board-modal-container"


class MoveType(Enum):
    """Enum for move types."""
    NORMAL = 1
    PROMOTION = 2


class ChesscomGrabber(Grabber):
    """
    Grabber implementation for chess.com.

    This class provides methods to interact with the chess.com website,
    such as finding the board, determining the player's color, and
    retrieving the move list.
    """

    def __init__(self, chrome_url, chrome_session_id):
        """
        Initializes the ChesscomGrabber.

        Args:
            chrome_url (str): The URL of the ChromeDriver.
            chrome_session_id (str): The ID of the Chrome session.
        """
        super().__init__(chrome_url, chrome_session_id)

    def update_board_elem(self):
        """
        Updates the board element.

        Finds the board element on the chess.com website and stores it.
        """
        try:
            self._board_elem = self.chrome.find_element(By.XPATH, BOARD_PLAY_COMPUTER_XPATH)
        except NoSuchElementException:
            try:
                self._board_elem = self.chrome.find_element(By.XPATH, BOARD_SINGLE_XPATH)
            except NoSuchElementException:
                self._board_elem = None

    def is_white(self):
        """
        Determines if the player is playing as white.

        Finds the coordinates elements on the board and uses the first number text to find out the player color.
        Returns:
            bool: True if the player is white, False if black, None if unknown.
        """
        try:
            coordinates = self.chrome.find_element(By.XPATH, BOARD_PLAY_COMPUTER_XPATH + SQUARE_XPATH)
            square_names = coordinates.find_elements(By.XPATH, SQUARE_XPATH)
        except NoSuchElementException:
            try:
                coordinates_elements = self.chrome.find_elements(By.XPATH, BOARD_SINGLE_XPATH + SQUARE_XPATH)
                coordinates = [x for x in coordinates_elements if x.get_attribute("class") == COORDINATES_CLASS][0]
                square_names = coordinates.find_elements(By.XPATH, SQUARE_XPATH)
            except NoSuchElementException:
                return None

        if not square_names:
            return None

        try:
            first_number_text = square_names[0].text
            return first_number_text == "1"
        except:
            return None

    def is_game_over(self) -> bool:
        """
        Checks if the game is over by looking for the game over modal.
        Returns:
            bool: True if the game is over, False otherwise.
        """
        try:
            WebDriverWait(self.chrome, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, GAME_OVER_WINDOW_CLASS))
            )
            return True
        except TimeoutException:
            return False

    def get_move_list(self):
        """
        Gets the list of moves from the chess.com website.

        Returns:
            list: A list of moves, e.g., ["e4", "c5", "Nf3"].
        """
        move_list = []
        try:
            move_list_elem = self.chrome.find_element(By.CLASS_NAME, MOVE_LIST_PLAY_CLASS)
        except NoSuchElementException:
            try:
                move_list_elem = self.chrome.find_element(By.CLASS_NAME, MOVE_LIST_SWAP_CLASS)
            except NoSuchElementException:
                return None

        moves = move_list_elem.find_elements(By.CSS_SELECTOR, MOVE_NODE_SELECTOR)

        for move in moves:
            move_data = self.process_move(move)
            if move_data:
                move_list.append(move_data)

        return move_list

    def process_move(self, move_element):
        """
        Process a move element to extract the move information.

        Args:
            move_element (WebElement): The move element.
        Returns:
            str: The processed move information, or None if the move is invalid.
        """
        move_class = move_element.get_attribute("class")
        if not ("white-move" in move_class or "black-move" in move_class):
            return None

        try:
            figurine_elem = move_element.find_element(By.CSS_SELECTOR, FIGURINE_SELECTOR)
            figure = figurine_elem.get_attribute("data-figurine")
        except NoSuchElementException:
            figure = None

        move_type = MoveType.NORMAL
        if figure is not None and "=" in move_element.text:
            move_type = MoveType.PROMOTION

        move_data = move_element.text
        if move_type == MoveType.PROMOTION:
            move_data += figure

        # Mark the move as processed
        self.chrome.execute_script("arguments[0].setAttribute('data-processed', 'true')", move_element)

        # If the move is a check, add the + in the end
        if "+" in move_data:
            move_data = move_data.replace("+", "")
            move_data += "+"

        return move_data

    def is_game_puzzles(self):
        """
        Checks if the current game is a puzzle.

        Returns:
            bool: False, since chess.com has a different way to find if it is a puzzle.
        """
        return False

    def click_puzzle_next(self):
        pass

    def click_game_next(self):
        pass

    def make_mouseless_move(self, move, move_count):
        pass
