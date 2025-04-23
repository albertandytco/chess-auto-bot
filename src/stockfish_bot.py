import multiprocess
from multiprocessing.connection import Connection
from stockfish import Stockfish
import pyautogui
import time
import sys
import os
import chess
import re
from grabbers.chesscom_grabber import ChesscomGrabber
from grabbers.lichess_grabber import LichessGrabber
from utilities import char_to_num
import keyboard


class StockfishBot(multiprocess.Process):
    """
    A class representing a Stockfish chess bot that interacts with a chess website.
    """
    # Constants for easier configuration
    BONGCLOUD_MOVES = ["e2e3", "e7e6", "e1e2", "e8e7"]
    MOUSE_LATENCY_DEFAULT = 0.1
    PROMOTION_OFFSET = {
        "n": 1,  # Knight promotion
        "r": 2,  # Rook promotion
        "b": 3,  # Bishop promotion
        "q": 0,  # Queen promotion
    }
    OVERLAY_WAIT_KEY = "3"

    def __init__(
        self,
        chrome_url: str,
        chrome_session_id: str,
        website: str,
        pipe: Connection,
        overlay_queue: multiprocess.Queue,
        stockfish_path: str,
        **kwargs
    ):
        multiprocess.Process.__init__(self)

        self.chrome_url = chrome_url
        self.chrome_session_id = chrome_session_id
        self.website = website
        self.pipe = pipe
        self.overlay_queue = overlay_queue
        self.stockfish_path: str = stockfish_path

        # Configuration from kwargs
        self.enable_manual_mode: bool = kwargs.get("enable_manual_mode", False)
        self.enable_mouseless_mode: bool = kwargs.get("enable_mouseless_mode", False)
        self.enable_non_stop_puzzles: bool = kwargs.get("enable_non_stop_puzzles", False)
        self.enable_non_stop_matches: bool = kwargs.get("enable_non_stop_matches", False)
        self.mouse_latency = kwargs.get("mouse_latency", StockfishBot.MOUSE_LATENCY_DEFAULT)
        self.bongcloud: bool = kwargs.get("bongcloud", False)
        self.slow_mover: bool = kwargs.get("slow_mover", False)
        self.skill_level: int = kwargs.get("skill_level", 0)
        self.stockfish_depth: int = kwargs.get("stockfish_depth", 15)
        self.memory = kwargs.get("memory", 128)
        self.cpu_threads = kwargs.get("cpu_threads", 1)
        self.mouse_latency = mouse_latency
        self.bongcloud = bongcloud
        self.slow_mover = slow_mover
        self.skill_level = skill_level
        self.stockfish_depth = stockfish_depth
        self.grabber = None
        self.memory = memory
        self.cpu_threads = cpu_threads
        self.is_white: bool = None
        self.exit = False

    def close_threads(self):
        """
        Close all threads.
        """
        self.exit = True
        self.grabber.close_chrome()

    # Converts a move to screen coordinates
    # Example: "a1" -> (x, y)
    def move_to_screen_pos(self, move: str) -> tuple[int, int]:
        # Get the absolute top left corner of the website
        canvas_x_offset, canvas_y_offset = self.grabber.get_top_left_corner()

        # Get the absolute board position
        board_x = canvas_x_offset + self.grabber.get_board().location["x"]
        board_y = canvas_y_offset + self.grabber.get_board().location["y"]

        # Get the square size
        square_size = self.grabber.get_board().size['width'] / 8

        # Convert char to number and adjust the index
        col_index = char_to_num(move[0]) - 1
        row_index = int(move[1])

        # Depending on the player color, the board is flipped, so the coordinates need to be adjusted
        if self.is_white:
            x = board_x + square_size * col_index + square_size / 2
            y = board_y + square_size * (8 - row_index) + square_size / 2
        else:
            x = board_x + square_size * (7 - col_index) + square_size / 2
            y = board_y + square_size * (row_index - 1) + square_size / 2

        return int(x), int(y)

    def get_move_pos(self, move: str) -> tuple[tuple[int, int], tuple[int, int]]:
        # Get the start and end position screen coordinates
        start_pos_x, start_pos_y = self.move_to_screen_pos(move[0:2])
        end_pos_x, end_pos_y = self.move_to_screen_pos(move[2:4])

        return (start_pos_x, start_pos_y), (end_pos_x, end_pos_y)

    def make_move(self, move: str):
        """
        Makes a move on the screen, including handling piece promotions.
        """
        # Get the start and end position screen coordinates
        start_pos, end_pos = self.get_move_pos(move)

        # Drag the piece from the start to the end position
        pyautogui.moveTo(start_pos[0], start_pos[1])
        time.sleep(self.mouse_latency)  # Add mouse latency
        pyautogui.dragTo(end_pos[0], end_pos[1])

        # Handle promotion
        if len(move) == 5:  # Promotion
            time.sleep(0.1)  # Small delay

            # Calculate the y-offset based on the promotion piece
            promotion_piece = move[4]
            offset = StockfishBot.PROMOTION_OFFSET.get(promotion_piece, 0)

            # Calculate the y position of the promotion piece
            promotion_y = int(move[3]) - offset
            promotion_pos_x, promotion_pos_y = self.move_to_screen_pos(move[2] + str(promotion_y))

            pyautogui.moveTo(x=promotion_pos_x, y=promotion_pos_y)
            pyautogui.click(button="left")

    def wait_for_gui_to_delete(self):
        while self.pipe.recv() != "DELETE":
            pass

    def go_to_next_puzzle(self):
        self.grabber.click_puzzle_next()
        self.pipe.send("RESTART")
        self.wait_for_gui_to_delete()

    def find_new_online_match(self):
        time.sleep(2)
        self.grabber.click_game_next()
        self.pipe.send("RESTART")
        self.wait_for_gui_to_delete()

    def run(self):
        """
        Main loop for the Stockfish bot.
        """
        try:
            if self.website == "chesscom":
                self.grabber = ChesscomGrabber(self.chrome_url, self.chrome_session_id)
            elif self.website is None:
                raise ValueError("Website cannot be None")
            else:
            self.grabber = LichessGrabber(self.chrome_url, self.chrome_session_id)

        # Initialize Stockfish
        parameters = {
            "Threads": self.cpu_threads,
            "Hash": self.memory,
            "Ponder": "true",
            "Slow Mover": self.slow_mover,
            "Skill Level": self.skill_level
        }

            # Check if stockfish exists
            if not os.path.exists(self.stockfish_path):
                self.pipe.send("ERR_EXE")
                return
            
            # Create stockfish instance
            stockfish = Stockfish(path=self.stockfish_path, depth=self.stockfish_depth, parameters=parameters)
        except PermissionError:
            self.pipe.send("ERR_PERM")
            return
        except OSError:
            self.pipe.send("ERR_EXE")
            return
        except ValueError as e:
            print(e)
            self.pipe.send("ERR")
            return

        try:
            # Initialize the grabber and check if the board exists
            self.grabber.update_board_elem()
            if self.grabber.get_board() is None:
                self.pipe.send("ERR_BOARD")
                return

            # Determine the player's color
            self.is_white = self.grabber.is_white()
            if self.is_white is None:
                self.pipe.send("ERR_COLOR")
                return

            # Get the starting position and check if there are any
            move_list = self.grabber.get_move_list()
            if move_list is None:
                self.pipe.send("ERR_MOVES")
                return

            # Check if the game is over by checking if the last move is a score
            score_pattern = r"([0-9]+)\-([0-9]+)"
            if len(move_list) > 0 and re.match(score_pattern, move_list[-1]):
                self.pipe.send("ERR_GAMEOVER")
                return

            # Setup the board and stockfish
            board = chess.Board()
            for move in move_list:
                board.push_san(move)
            move_list_uci = [move.uci() for move in board.move_stack]
            stockfish.set_position(move_list_uci)

            # Notify the GUI that the bot is ready
            self.pipe.send("START")

            # Send the existing moves to the GUI
            if len(move_list) > 0:
                self.pipe.send(f"M_MOVE,{','.join(move_list)}")

            # Main game loop
            while not self.exit:
                # Check if it's the player's turn
                if (self.is_white and board.turn == chess.WHITE) or (
                    not self.is_white and board.turn == chess.BLACK
                ):
                    # Determine the move
                    move_count = len(board.move_stack)
                    move = self.get_bot_move(board, stockfish, move_count)

                    # Manual mode handling
                    if self.enable_manual_mode:
                        self.handle_manual_mode(board, stockfish, move, move_list)
                    else:
                        self.execute_bot_move(board, stockfish, move, move_list)

                    # Check if the game is over
                    if board.is_game_over():
                        self.handle_game_over()
                        return

                    time.sleep(0.1)
                else:
                    # Wait for opponent's move
                    if not self.wait_for_opponent_move(board, stockfish, move_list):
                        return

                    # Check if the game is over
                    if board.is_game_over():
                        self.handle_game_over()
                        return

        except Exception as e:
            self.pipe.send("ERR")
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

    def get_bot_move(self, board: chess.Board, stockfish: Stockfish, move_count: int) -> str:
        """Determines the bot's move."""
        move = None
        # Bongcloud logic
        if self.bongcloud and move_count <= 3:
            move = StockfishBot.BONGCLOUD_MOVES[move_count]
            if not board.is_legal(chess.Move.from_uci(move)):
                move = stockfish.get_best_move()
        else:
            move = stockfish.get_best_move()

        return move

    def handle_manual_mode(self, board: chess.Board, stockfish: Stockfish, move: str, move_list: list):
        """Handles manual mode, waiting for user input."""
        move_start_pos, move_end_pos = self.get_move_pos(move)
        self.overlay_queue.put([((move_start_pos), (move_end_pos))])
        self_moved = False
        while not self.exit:
            if keyboard.is_pressed(StockfishBot.OVERLAY_WAIT_KEY):
                break

            current_move_list = self.grabber.get_move_list()
            if len(move_list) != len(current_move_list):
                self_moved = True
                move_list = current_move_list
                move_san = move_list[-1]
                move = board.parse_san(move_san).uci()
                board.push_uci(move)
                stockfish.make_moves_from_current_position([move])
                break

        if not self_moved:
            self.execute_bot_move(board, stockfish, move, move_list)
        self.overlay_queue.put([])

    def execute_bot_move(self, board: chess.Board, stockfish: Stockfish, move: str, move_list: list):
        """Executes the bot's move."""
        move_san = board.san(chess.Move.from_uci(move))
        board.push_uci(move)
        stockfish.make_moves_from_current_position([move])
        move_list.append(move_san)

        if self.enable_mouseless_mode and not self.grabber.is_game_puzzles():
            self.grabber.make_mouseless_move(move, len(board.move_stack))
        else:
            self.make_move(move)

        self.pipe.send(f"S_MOVE,{move_san}")

    def handle_game_over(self):
        """Handles game over scenarios."""
        if self.enable_non_stop_puzzles and self.grabber.is_game_puzzles():
            self.go_to_next_puzzle()
        elif self.enable_non_stop_matches and not self.enable_non_stop_puzzles:
            self.find_new_online_match()

    def wait_for_opponent_move(self, board: chess.Board, stockfish: Stockfish, move_list: list) -> bool:
        """Waits for the opponent's move."""
        previous_move_list = move_list.copy()
        while not self.exit:
            if self.grabber.is_game_over():
                self.handle_game_over()
                return False

            move_list = self.grabber.get_move_list()
            if move_list is None:
                self.pipe.send("ERR_MOVES")
                return False

            if len(move_list) > len(previous_move_list):
                # Get the opponent's move
                move = move_list[-1]
                self.pipe.send(f"S_MOVE,{move}")
                board.push_san(move)
                stockfish.make_moves_from_current_position([str(board.peek())])
                return True

        return False
                        move = stockfish.get_best_move()

                    # Wait for keypress or player movement if in manual mode
                    self_moved = False
                    if self.enable_manual_mode:
                        move_start_pos, move_end_pos = self.get_move_pos(move)
                        self.overlay_queue.put([
                            ((int(move_start_pos[0]), int(move_start_pos[1])), (int(move_end_pos[0]), int(move_end_pos[1]))),
                        ])
                        while True:
                            if keyboard.is_pressed("3"):
                                break

                            if len(move_list) != len(self.grabber.get_move_list()):
                                self_moved = True
                                move_list = self.grabber.get_move_list()
                                move_san = move_list[-1]
                                move = board.parse_san(move_san).uci()
                                board.push_uci(move)
                                stockfish.make_moves_from_current_position([move])
                                break

                    if not self_moved:
                        move_san = board.san(chess.Move(chess.parse_square(move[0:2]), chess.parse_square(move[2:4])))
                        board.push_uci(move)
                        stockfish.make_moves_from_current_position([move])
                        move_list.append(move_san)
                        if self.enable_mouseless_mode and not self.grabber.is_game_puzzles():
                            self.grabber.make_mouseless_move(move, move_count + 1)
                        else:
                            self.make_move(move)

                    self.overlay_queue.put([])

                    # Send the move to the GUI
                    self.pipe.send("S_MOVE" + move_san)

                    # Check if the game is over
                    if board.is_checkmate():
                        # Send restart message to GUI
                        if self.enable_non_stop_puzzles and self.grabber.is_game_puzzles():
                            self.go_to_next_puzzle()
                        elif self.enable_non_stop_matches and not self.enable_non_stop_puzzles:
                            self.find_new_online_match()
                        return

                    time.sleep(0.1)

                # Wait for a response from the opponent
                # by finding the differences between
                # the previous and current position
                previous_move_list = move_list.copy()
                while True:
                    if self.grabber.is_game_over():
                        # Send restart message to GUI
                        if self.enable_non_stop_puzzles and self.grabber.is_game_puzzles():
                            self.go_to_next_puzzle()
                        elif self.enable_non_stop_matches and not self.enable_non_stop_puzzles:
                            self.find_new_online_match()
                        return
                    move_list = self.grabber.get_move_list()
                    if move_list is None:
                        return
                    if len(move_list) > len(previous_move_list):
                        break

                # Get the move that the opponent made
                move = move_list[-1]
                self.pipe.send("S_MOVE" + move)
                board.push_san(move)
                stockfish.make_moves_from_current_position([str(board.peek())])
                if board.is_checkmate():
                    # Send restart message to GUI
                    if self.enable_non_stop_puzzles and self.grabber.is_game_puzzles():
                        self.go_to_next_puzzle()
                    elif self.enable_non_stop_matches and not self.enable_non_stop_puzzles:
                        self.find_new_online_match()
                    return
        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
