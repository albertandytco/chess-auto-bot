from enum import Enum

from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from grabbers.grabber import Grabber


class MoveType(Enum):
    NORMAL = 1
    PUZZLE = 2
    UNKNOWN = 3


class LichessGrabber(Grabber):
    """
    Concrete class for interacting with lichess.org.
    """

    # Constants for XPATH selectors
    BOARD_XPATH = '//*[@id="main-wrap"]/main/div[1]/div[1]/div/cg-container'
    PUZZLE_BOARD_XPATH = '/html/body/div[2]/main/div[1]/div/cg-container'
    GAME_OVER_XPATH = '//*[@id="main-wrap"]/main/aside/div/section[2]'
    PUZZLE_GAME_OVER_XPATH = '/html/body/div[2]/main/div[2]/div[3]/div[1]'
    NORMAL_MOVE_LIST_XPATH = '//*[@id="main-wrap"]/main/div[1]/rm6/l4x'
    NORMAL_MOVE_LIST_EMPTY_XPATH = '//*[@id="main-wrap"]/main/div[1]/rm6'
    PUZZLE_MOVE_LIST_XPATH = '/html/body/div[2]/main/div[2]/div[2]/div'
    PUZZLE_TEXT_XPATH = "/html/body/div[2]/main/aside/div[1]/div[1]/div/p[1]"
    PUZZLE_NEXT_BUTTON_XPATH = "/html/body/div[2]/main/div[2]/div[3]/a"
    PUZZLE_NEXT_BUTTON_2_XPATH = '//*[@id="main-wrap"]/main/div[2]/div[3]/div[3]/a[2]'
    NEW_GAME_BUTTON_XPATH = "//*[contains(text(), 'New opponent')]"
    PIECE_SQUARE_XPATH = "./*"

    def __init__(self, chrome_url, chrome_session_id):
        super().__init__(chrome_url, chrome_session_id)
        self.move_type = MoveType.UNKNOWN

    def update_board_elem(self):
        """
        Updates the internal representation of the board element.
        """
        try:
            # Try finding the normal board
            self._board_elem = self.chrome.find_element(By.XPATH, self.BOARD_XPATH)
            self.move_type = MoveType.NORMAL
        except NoSuchElementException:
            try:
                # Try finding the board in the puzzles page
                self._board_elem = self.chrome.find_element(By.XPATH, self.PUZZLE_BOARD_XPATH)
                self.move_type = MoveType.PUZZLE
            except NoSuchElementException:
                self._board_elem = None
                self.move_type = MoveType.UNKNOWN

    def is_white(self):
        """
        Determines if the player is playing as white.
        Returns:
            bool: True if the player is white, False if black, None if unknown.
        """
        try:
            # Get the first element inside the board
            children = self._board_elem.find_elements(By.XPATH, self.PIECE_SQUARE_XPATH)
            first_child = children[0]
            
            # Check if the first child has the attribute of the white square
            return "white" in first_child.get_attribute("class")
        except (NoSuchElementException, IndexError, AttributeError):
            return None

    def is_game_over(self):
        """
        Checks if the game is over.
        Returns:
            bool: True if the game is over, False otherwise.
        """
        try:
            if self.move_type == MoveType.NORMAL:
                # Find the game over window
                self.chrome.find_element(By.XPATH, self.GAME_OVER_XPATH)
                return True
            elif self.move_type == MoveType.PUZZLE:
                # Check if the puzzle is complete
                game_over_window = self.chrome.find_element(By.XPATH, self.PUZZLE_GAME_OVER_XPATH)
                return game_over_window.get_attribute("class") == "complete"
            else:
                return False
        except NoSuchElementException:
            return False

    def is_game_puzzles(self):
        """
        Checks if the current game is a puzzle.
        Returns:
            bool: True if it's a puzzle, False otherwise.
        """
        return self.move_type == MoveType.PUZZLE

    def get_move_list(self):
        """
        Gets the list of moves from the game.
        Returns:
            list: A list of moves, e.g., ["e4", "c5", "Nf3"].
        """
        try:
            # Wait for the element to be found
            if self.move_type == MoveType.NORMAL:
                move_list_elem = WebDriverWait(self.chrome, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.NORMAL_MOVE_LIST_XPATH))
                )
                
                #If the element does not have childs, check if it exist the empty element
                if not move_list_elem.find_elements(By.XPATH, "./*"):
                    self.chrome.find_element(By.XPATH, self.NORMAL_MOVE_LIST_EMPTY_XPATH)
                    return []
                
                # Find all children elements that have the class move
                children = move_list_elem.find_elements(By.XPATH, ".//*[contains(@class, 'move')]")
            elif self.move_type == MoveType.PUZZLE:
                move_list_elem = self.chrome.find_element(By.XPATH, self.PUZZLE_MOVE_LIST_XPATH)
                # Find all elements with the move tag
                children = move_list_elem.find_elements(By.TAG_NAME, "move")
            else:
                return None

            # Extract moves from elements
            moves = [child.text.strip() for child in children]
            return moves

        except (NoSuchElementException, TimeoutException):
            return None

    def click_puzzle_next(self):
        """
        Clicks the "next puzzle" button.
        """
        try:
            next_button = self.chrome.find_element(By.XPATH, self.PUZZLE_NEXT_BUTTON_XPATH)
        except NoSuchElementException:
            try:
                next_button = self.chrome.find_element(By.XPATH, self.PUZZLE_NEXT_BUTTON_2_XPATH)
            except NoSuchElementException:
                return

        self.chrome.execute_script("arguments[0].click();", next_button)

    def click_game_next(self):
        """
        Clicks the "new game" button.
        """
        try:
            next_button = self.chrome.find_element(By.XPATH, self.NEW_GAME_BUTTON_XPATH)
        except NoSuchElementException:
            return

        self.chrome.execute_script("arguments[0].click();", next_button)

    def make_mouseless_move(self, move, move_count):
        """
        Makes a move without moving the mouse.
        Args:
            move (string): The move in uci format.
            move_count (int): The move count.
        """
        message = f'{{"t":"move","d":{{"u":"{move}","b":1,"a":{move_count}}}}}'
        script = f'lichess.socket.ws.send(JSON.stringify({message}))'
        self.chrome.execute_script(script)
