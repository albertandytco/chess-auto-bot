import os
import multiprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import keyboard
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from overlay import run
from stockfish_bot import StockfishBot


class GUI:
    def __init__(self, master):
        self.master = master

        # Used for closing the threads
        # Constants
        self.STATUS_INACTIVE = "Inactive"
        self.STATUS_RUNNING = "Running"
        self.COLOR_RED = "red"
        self.COLOR_GREEN = "green"
        self.DEFAULT_MOUSE_LATENCY = 0.0
        self.DEFAULT_SLOW_MOVER = 100
        self.DEFAULT_SKILL_LEVEL = 20
        self.DEFAULT_STOCKFISH_DEPTH = 15
        self.DEFAULT_MEMORY = 512
        self.DEFAULT_CPU_THREADS = 1
        self.WINDOW_TITLE = "Chess"
        self.exit = False

        # The Selenium Chrome driver
        self.chrome = None

        # # Used for storing the Stockfish Bot class Instance
        # self.stockfish_bot = None
        self.chrome_url = None
        self.chrome_session_id = None

        # Used for the communication between the GUI
        # and the Stockfish Bot process.
        self.stockfish_bot_pipe = None
        self.overlay_screen_pipe = None

        # The Stockfish Bot process
        self.stockfish_bot_process = None
        self.overlay_screen_process = None
        self.restart_after_stopping = False

        # Used for storing the match moves
        self.match_moves = []

        # Set the window properties
        master.title(self.WINDOW_TITLE)
        master.geometry("")
        master.iconphoto(True, tk.PhotoImage(file="src/assets/pawn_32x32.png"))  # Replace with correct path if needed
        master.resizable(False, False)
        master.attributes("-topmost", True)
        master.protocol("WM_DELETE_WINDOW", self.on_close_listener)

        # Change the style
        style = ttk.Style()
        style.theme_use("clam")

        # Left frame
        left_frame = tk.Frame(master)

        # Create the status text
        status_label = tk.Frame(left_frame)
        tk.Label(status_label, text="Status:").pack(side=tk.LEFT)
        self.status_text = tk.Label(status_label, text=self.STATUS_INACTIVE, fg=self.COLOR_RED)
        self.status_text.pack()
        status_label.pack(anchor=tk.NW)

        # Create the website chooser radio buttons
        self.website = tk.StringVar(value="chesscom")
        self.chesscom_radio_button = tk.Radiobutton(
            left_frame,
            text="Chess.com",
            variable=self.website,
            value="chesscom",
        )
        self.chesscom_radio_button.pack(anchor=tk.NW)
        self.lichess_radio_button = tk.Radiobutton(
            left_frame,
            text="Lichess.org",
            variable=self.website,
            value="lichess"
        )  # Fix typo: Lichess.org
        self.lichess_radio_button.pack(anchor=tk.NW)

        # Create the open browser button
        self.opening_browser = False
        self.opened_browser = False
        self.open_browser_button = tk.Button(
            left_frame,
            text="Open Browser",
            command=self.on_open_browser_button_listener,
        )
        self.open_browser_button.pack(anchor=tk.NW)

        # Create the start button
        self.running = False
        self.start_button = tk.Button(
            left_frame, text="Start", command=self.on_start_button_listener
        )
        self.start_button["state"] = "disabled"
        self.start_button.pack(anchor=tk.NW, pady=5)

        # Create the manual mode checkbox
        self.enable_manual_mode = tk.BooleanVar(value=False)
        self.manual_mode_checkbox = tk.Checkbutton(
            left_frame,
            text="Manual Mode",
            variable=self.enable_manual_mode,
            command=self.on_manual_mode_checkbox_listener,
        )
        self.manual_mode_checkbox.pack(anchor=tk.NW)

        # Create the manual mode instructions
        self.manual_mode_frame = tk.Frame(left_frame)
        self.manual_mode_label = tk.Label(
            self.manual_mode_frame, text="\u2022 Press 3 to make a move"
        )  # Add instructions for manual mode
        self.manual_mode_label.pack(anchor=tk.NW)

        # Create the mouseless mode checkbox
        self.enable_mouseless_mode = tk.BooleanVar(value=False)
        self.mouseless_mode_checkbox = tk.Checkbutton(  # Add checkbox for mouseless mode
            left_frame,
            text="Mouseless Mode",
            variable=self.enable_mouseless_mode
        )
        self.mouseless_mode_checkbox.pack(anchor=tk.NW)

        # Create the non-stop puzzles check button
        self.enable_non_stop_puzzles = tk.IntVar(value=0)
        self.non_stop_puzzles_check_button = tk.Checkbutton(
            left_frame,
            text="Non-stop puzzles",
            variable=self.enable_non_stop_puzzles,
        )
        self.non_stop_puzzles_check_button.pack(anchor=tk.NW)

        # Create the non-stop matches check button
        self.enable_non_stop_matches = tk.IntVar(value=0)
        self.non_stop_matches_check_button = tk.Checkbutton(left_frame, text="Non-stop online matches",
                                                            variable=self.enable_non_stop_matches)
        self.non_stop_matches_check_button.pack(anchor=tk.NW)  # Add checkbox for non-stop online matches

        # Create the bongcloud check button
        self.enable_bongcloud = tk.IntVar()  # Add checkbox for bongcloud mode
        self.bongcloud_check_button = tk.Checkbutton(
            left_frame,
            text="Bongcloud",
            variable=self.enable_bongcloud,
        )
        self.bongcloud_check_button.pack(anchor=tk.NW)

        # Create the mouse latency scale
        # Scale for mouse latency
        self.mouse_latency = tk.DoubleVar(value=self.DEFAULT_MOUSE_LATENCY)
        mouse_latency_frame = tk.Frame(left_frame)
        tk.Label(mouse_latency_frame, text="Mouse Latency (seconds)").pack(side=tk.LEFT, pady=(17, 0))
        self.mouse_latency = tk.DoubleVar(value=0.0)
        self.mouse_latency_scale = tk.Scale(mouse_latency_frame, from_=0.0, to=5, resolution=0.2, orient=tk.HORIZONTAL,
                                          variable=self.mouse_latency)
        self.mouse_latency_scale.pack()
        mouse_latency_frame.pack(anchor=tk.NW)
        
        # Separator
        separator_frame = tk.Frame(left_frame)
        separator = ttk.Separator(separator_frame, orient="horizontal")
        separator.grid(row=0, column=0, sticky="ew")
        label = tk.Label(separator_frame, text="Stockfish parameters")
        label.grid(row=0, column=0, padx=40)
        separator_frame.pack(anchor=tk.NW, pady=10, expand=True, fill=tk.X)

        # Create the Slow mover entry field
        slow_mover_frame = tk.Frame(left_frame)
        self.slow_mover_label = tk.Label(slow_mover_frame, text="Slow Mover")  # Add label for slow mover
        self.slow_mover_label.pack(side=tk.LEFT)
        self.slow_mover = tk.IntVar(value=self.DEFAULT_SLOW_MOVER)
        self.slow_mover_entry = tk.Entry(
            slow_mover_frame, textvariable=self.slow_mover, justify="center", width=8
        )  # Add entry for slow mover
        self.slow_mover_entry.pack()
        slow_mover_frame.pack(anchor=tk.NW)

        # Create the skill level scale
        skill_level_frame = tk.Frame(left_frame)
        tk.Label(skill_level_frame, text="Skill Level").pack(side=tk.LEFT, pady=(19, 0))
        self.skill_level = tk.IntVar(value=20)
        self.skill_level_scale = tk.Scale(  # Add scale for skill level
            skill_level_frame,
            from_=0,
            to=20,
            orient=tk.HORIZONTAL,
            variable=self.skill_level,
        )
        self.skill_level_scale.pack()
        skill_level_frame.pack(anchor=tk.NW)

        # Create the Stockfish depth scale
        stockfish_depth_frame = tk.Frame(left_frame)
        tk.Label(stockfish_depth_frame, text="Depth").pack(side=tk.LEFT, pady=19)
        self.stockfish_depth = tk.IntVar(value=15)
        self.stockfish_depth_scale = tk.Scale(
            stockfish_depth_frame,  # Add scale for Stockfish depth
            from_=1,
            to=20,
            orient=tk.HORIZONTAL,
            variable=self.stockfish_depth,
        )
        self.stockfish_depth_scale.pack()
        stockfish_depth_frame.pack(anchor=tk.NW)

        # Create the memory entry field
        memory_frame = tk.Frame(left_frame)
        tk.Label(memory_frame, text="Memory").pack(side=tk.LEFT)  # Add label for memory
        self.memory = tk.IntVar(value=self.DEFAULT_MEMORY)
        self.memory_entry = tk.Entry(  # Add entry for memory
            memory_frame, textvariable=self.memory, justify="center", width=9,
        )
        self.memory_entry.pack(side=tk.LEFT)
        tk.Label(memory_frame, text="MB").pack()
        memory_frame.pack(anchor=tk.NW, pady=(0, 15))

        # Create the CPU threads entry field
        cpu_threads_frame = tk.Frame(left_frame)
        tk.Label(cpu_threads_frame, text="CPU Threads").pack(side=tk.LEFT)  # Add label for CPU threads
        self.cpu_threads = tk.IntVar(value=self.DEFAULT_CPU_THREADS)
        self.cpu_threads_entry = tk.Entry(  # Add entry for CPU threads
            cpu_threads_frame, textvariable=self.cpu_threads, justify="center", width=7,
        )
        self.cpu_threads_entry.pack()
        cpu_threads_frame.pack(anchor=tk.NW)

        # Separator
        separator_frame = tk.Frame(left_frame)
        separator = ttk.Separator(separator_frame, orient="horizontal")
        separator.grid(row=0, column=0, sticky="ew")
        label = tk.Label(separator_frame, text="Misc")
        label.grid(row=0, column=0, padx=82)
        separator_frame.pack(anchor=tk.NW, pady=10, expand=True, fill=tk.X)

        # Create the topmost check button
        self.enable_topmost = tk.IntVar(value=1)
        self.topmost_check_button = tk.Checkbutton(
            left_frame,
            text="Window stays on top",
            variable=self.enable_topmost,
            onvalue=1,
            offvalue=0,
            command=self.on_topmost_check_button_listener,
        )
        self.topmost_check_button.pack(anchor=tk.NW)

        # Create the select stockfish button
        self.stockfish_path = ""
        self.select_stockfish_button = tk.Button(
            left_frame,
            text="Select Stockfish",
            command=self.on_select_stockfish_button_listener,
        )
        self.select_stockfish_button.pack(anchor=tk.NW)

        # Create the stockfish path text
        self.stockfish_path_text = tk.Label(left_frame, text="", wraplength=180)  # Add text for stockfish path
        self.stockfish_path_text.pack(anchor=tk.NW)

        left_frame.grid(row=0, column=0, padx=5, sticky=tk.NW)

        # Right frame
        right_frame = tk.Frame(master)

        # Treeview frame
        treeview_frame = tk.Frame(right_frame)

        # Create the moves Treeview
        self.tree = ttk.Treeview(
            treeview_frame,
            column=("#", "White", "Black"),
            show="headings",
            height=23,
            selectmode="browse",
        )
        self.tree.pack(anchor=tk.NW, side=tk.LEFT)  # Add Treeview

        # # Add the scrollbar to the Treeview
        self.vsb = ttk.Scrollbar(
            treeview_frame,
            orient="vertical",
            command=self.tree.yview
        )
        self.vsb.pack(fill=tk.Y, expand=True)
        self.tree.configure(yscrollcommand=self.vsb.set)

        # Create the columns
        self.tree.column("# 1", anchor=tk.CENTER, width=35)
        self.tree.heading("# 1", text="#")
        self.tree.column("# 2", anchor=tk.CENTER, width=60)
        self.tree.heading("# 2", text="White")
        self.tree.column("# 3", anchor=tk.CENTER, width=60)
        self.tree.heading("# 3", text="Black")

        treeview_frame.pack(anchor=tk.NW)

        # Create the export PGN button
        self.export_pgn_button = tk.Button(
            right_frame, text="Export PGN", command=self.on_export_pgn_button_listener
        )  # Add button for exporting PGN
        self.export_pgn_button.pack(anchor=tk.NW, fill=tk.X)

        right_frame.grid(row=0, column=1, sticky=tk.NW)

        # Start the process checker thread
        process_checker_thread = threading.Thread(target=self.process_checker_thread)
        process_checker_thread.start()

        # Start the browser checker thread
        browser_checker_thread = threading.Thread(target=self.browser_checker_thread)
        browser_checker_thread.start()

        # Start the process communicator thread
        process_communicator_thread = threading.Thread(
            target=self.process_communicator_thread
        )
        process_communicator_thread.start()

        # Start the keyboard listener thread
        keyboard_listener_thread = threading.Thread(  # Add keyboard listener thread
            target=self.keypress_listener_thread
        )
        keyboard_listener_thread.start()

    # Detects if the user pressed the close button
    def on_close_listener(self):  # Corrected the method name
        # Set self.exit to True so that the threads will stop
        self.exit = True
        self.master.destroy()

    # Detects if the Stockfish Bot process is running
    def process_checker_thread(self):
        while not self.exit:
            if (
                self.running
                and self.stockfish_bot_process is not None
                and not self.stockfish_bot_process.is_alive()
            ):
                self.on_stop_button_listener()

                # Restart the process if `restart_after_stopping` is True
                if self.restart_after_stopping:
                    self.restart_after_stopping = False
                    self.on_start_button_listener()

            # Add a sleep period to prevent high CPU usage
            time.sleep(0.1)

    # Detects if Selenium Chromedriver is running
    def browser_checker_thread(self):
        while not self.exit:
            try:
                if (
                    self.opened_browser
                    and self.chrome is not None
                    and "target window already closed"
                    in self.chrome.get_log("driver")[-1]["message"]
                ):  # Check if the browser has been closed
                    self.opened_browser = False

                    # Set Opening Browser button state to closed.
                    self.open_browser_button["text"] = "Open Browser"
                    self.open_browser_button["state"] = "normal"
                    self.open_browser_button.update()

                    # Stop the bot
                    self.on_stop_button_listener()
                    self.chrome = None
            except IndexError:
                pass

            # Add a sleep period to prevent high CPU usage
            time.sleep(0.1)

    # Responsible for communicating with the Stockfish Bot process
    # The pipe can receive the following commands:
    # - "START": Resets and starts the Stockfish Bot
    # - "S_MOVE": Sends the Stockfish Bot a single move to make
    #   Ex. "S_MOVEe4
    # - "M_MOVE": Sends the Stockfish Bot multiple moves to make
    #   Ex. "S_MOVEe4,c5,Nf3
    # - "ERR_EXE": Notifies the GUI that the Stockfish Bot can't initialize Stockfish
    # - "ERR_PERM": Notifies the GUI that the Stockfish Bot can't execute the Stockfish executable
    # - "ERR_BOARD": Notifies the GUI that the Stockfish Bot can't find the board
    # - "ERR_COLOR": Notifies the GUI that the Stockfish Bot can't find the player color
    # - "ERR_MOVES": Notifies the GUI that the Stockfish Bot can't find the moves list
    # - "ERR_GAMEOVER": Notifies the GUI that the current game is already over
    # - "ERR": Notifies the GUI that an unhandled error has occurred
    def process_communicator_thread(self):
        while not self.exit:
            try:
                if (
                    self.stockfish_bot_pipe is not None
                    and self.stockfish_bot_pipe.poll()
                ):
                    data = self.stockfish_bot_pipe.recv()
                    if data == "START":
                        self.clear_tree()
                        self.match_moves = []

                        # Update the status text
                        self.status_text["text"] = self.STATUS_RUNNING
                        self.status_text["fg"] = self.COLOR_GREEN
                        self.status_text.update()

                        # Update the run button
                        self.start_button["text"] = "Stop"
                        self.start_button["state"] = "normal"
                        self.start_button["command"] = self.on_stop_button_listener
                        self.start_button.update()
                    elif data[:7] == "RESTART":
                        self.restart_after_stopping = True
                        self.stockfish_bot_pipe.send("DELETE")
                    elif data[:6] == "S_MOVE":
                        move = data[6:]
                        self.match_moves.append(move)
                        self.insert_move(move)
                        self.tree.yview_moveto(1)
                    elif data[:6] == "M_MOVE":
                        moves = data[6:].split(",")
                        self.match_moves += moves
                        self.set_moves(moves)
                        self.tree.yview_moveto(1)
                    elif data == "ERR_EXE":
                        self.show_error("Stockfish path provided is not valid!")
                    elif data == "ERR_PERM":
                        self.show_error("Stockfish path provided is not executable!")
                    elif data == "ERR_BOARD":
                        self.show_error("Can't find the board!")
                    elif data == "ERR_COLOR":
                        self.show_error("Can't find player color!")
                    elif data == "ERR_MOVES":
                        self.show_error("Can't find moves list!")
                    elif data == "ERR_GAMEOVER":
                        self.show_error("Game has already finished!")
                    elif data == "ERR":
                        self.show_error("Unhandled error has occurred!")
            except (BrokenPipeError, OSError):
                self.stockfish_bot_pipe = None

            # Add a sleep period to prevent high CPU usage
            time.sleep(0.1)

    def keypress_listener_thread(self):
        while not self.exit:
            time.sleep(0.1)
            if not self.opened_browser:  # Check if the browser is opened
                continue

            # Check if the buttons 1 and 2 are pressed to start and stop the bot
            if keyboard.is_pressed("1"):
                self.on_start_button_listener()  # Start
            elif keyboard.is_pressed("2"):
                self.on_stop_button_listener()

    def on_open_browser_button_listener(self):
        # Set Opening Browser button state to opening
        self.opening_browser = True
        self.open_browser_button["text"] = "Opening Browser..."
        self.open_browser_button["state"] = "disabled"
        self.open_browser_button.update()

        # Configure Chrome options
        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])  # Add options to avoid
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("useAutomationExtension", False)
        try:
            # Get ChromeDriver and install if necessary
            chrome_install = ChromeDriverManager().install()

            # Get the path to the ChromeDriver executable
            folder = os.path.dirname(chrome_install)
            chromedriver_path = os.path.join(folder, "chromedriver.exe")

            # Create the service object to start the webdriver
            service = ChromeService(chromedriver_path)
            self.chrome = webdriver.Chrome(
                service=service,
                options=options
            )
        except WebDriverException:
            # No chrome installed
            self.opening_browser = False
            self.open_browser_button["text"] = "Open Browser"
            self.open_browser_button["state"] = "normal"
            self.open_browser_button.update()
            self.show_error(
                "Error",
                "Cant find Chrome. You need to have Chrome installed for this to work.",
            )
            return
        except Exception as e:
            # Other error
            self.opening_browser = False
            self.open_browser_button["text"] = "Open Browser"
            self.open_browser_button["state"] = "normal"
            self.open_browser_button.update()
            self.show_error(
                f"An error occurred while opening the browser: {e}"
            )
            return

        # Open chess.com
        if self.website.get() == "chesscom":  # Open chess.com or lichess.org
            self.chrome.get("https://www.chess.com")
        else:
            # Open lichess.org
            self.chrome.get("https://www.lichess.org")

        # Build Stockfish Bot
        self.chrome_url = self.chrome.service.service_url
        self.chrome_session_id = self.chrome.session_id

        # Set Opening Browser button state to opened
        self.opening_browser = False
        self.opened_browser = True
        self.open_browser_button["text"] = "Browser is open"
        self.open_browser_button["state"] = "disabled"
        self.open_browser_button.update()

        # Enable run button
        self.start_button["state"] = "normal"
        self.start_button.update()

    def on_start_button_listener(self):
        # Check if Slow mover value is valid
        slow_mover = self.slow_mover.get()
        if slow_mover < 10 or slow_mover > 1000:
            self.show_error("Slow Mover must be between 10 and 1000")
            return

        # Check if stockfish path is not empty
        if self.stockfish_path == "":
            self.show_error("Stockfish path is empty")
            return

        # Check if mouseless mode is enabled when on chess.com
        if self.enable_mouseless_mode.get() == 1 and self.website.get() == "chesscom":
            tk.messagebox.showerror(
                "Error", "Mouseless mode is only supported on lichess.org"
            )
            return

        # Create the pipes used for the communication
        # between the GUI and the Stockfish Bot process
        parent_conn, child_conn = multiprocess.Pipe()
        self.stockfish_bot_pipe = parent_conn

        # Create the message queue that is used for the communication
        # between the Stockfish and the Overlay processes
        st_ov_queue = multiprocess.Queue()

        # Create the Stockfish Bot process
        self.stockfish_bot_process = StockfishBot(
            self.chrome_url,
            self.chrome_session_id,
            self.website.get(),
            child_conn,
            st_ov_queue,
            self.stockfish_path,
            self.enable_manual_mode.get() == 1,
            self.enable_mouseless_mode.get() == 1,  # Add the parameters from the GUI
            self.enable_non_stop_puzzles.get() == 1,  # Add the parameters from the GUI
            self.enable_non_stop_matches.get() == 1,  # Add the parameters from the GUI
            self.mouse_latency.get(),  # Add the parameters from the GUI
            self.enable_bongcloud.get() == 1,  # Add the parameters from the GUI
            self.slow_mover.get(),  # Add the parameters from the GUI
            self.skill_level.get(),  # Add the parameters from the GUI
            self.stockfish_depth.get(),  # Add the parameters from the GUI
            self.memory.get(),  # Add the parameters from the GUI
            self.cpu_threads.get(),
        )
        self.stockfish_bot_process.start()

        # Create the overlay
        self.overlay_screen_process = multiprocess.Process(
            target=run, args=(st_ov_queue,)
        )
        self.overlay_screen_process.start()

        # Update the run button
        self.running = True
        self.start_button["text"] = "Starting..."
        self.start_button["state"] = "disabled"
        self.start_button.update()

    def on_stop_button_listener(self):
        # Stop the Stockfish Bot process
        if self.stockfish_bot_process is not None:
            self.stockfish_bot_process.close_threads()
            self.stockfish_bot_process = None

        # Stop the overlay process
        if self.overlay_screen_process is not None:
            self.overlay_screen_process.kill()
            self.overlay_screen_process = None

        # Close all pipes
        self.close_pipes()


        # Update the status text
        self.running = False
        self.status_text["text"] = "Inactive"
        self.status_text["fg"] = "red"
        self.status_text.update()

        # Update the run button
        self.start_button["text"] = "Start"
        self.start_button["state"] = "normal"
        self.start_button["command"] = self.on_start_button_listener
        self.start_button.update()

    # Close all pipes
    def close_pipes(self):
        # Close the Stockfish Bot pipe
        if self.stockfish_bot_pipe is not None:
            self.stockfish_bot_pipe.close()
            self.stockfish_bot_pipe = None

        # Close the overlay pipe
        if self.overlay_screen_pipe is not None:
            self.overlay_screen_pipe.close()
            self.overlay_screen_pipe = None

    def on_topmost_check_button_listener(self):
        if self.enable_topmost.get() == 1:
            self.master.attributes("-topmost", True)
        else:
            self.master.attributes("-topmost", False)

    def on_export_pgn_button_listener(self):
        # Create the save file dialog
        f = filedialog.asksaveasfile(
            initialfile="match.pgn",
            defaultextension=".pgn",
            filetypes=[("Portable Game Notation", "*.pgn"), ("All Files", "*.*")],
        )
        if f is None:
            return

        # Write the PGN to the file
        data = ""
        for i in range(len(self.match_moves) // 2 + 1):
            if len(self.match_moves) % 2 == 0 and i == len(self.match_moves) // 2:
                continue
            data += str(i + 1) + ". "
            data += self.match_moves[i * 2] + " "
            if (i * 2) + 1 < len(self.match_moves):
                data += self.match_moves[i * 2 + 1] + " "
        f.write(data)
        f.close()

    def show_error(self, message: str):
        messagebox.showerror(
            "Error", message
        )

    def on_select_stockfish_button_listener(self):
        # Create the open file dialog
        f = filedialog.askopenfilename()
        if not f:  # if no file is selected
            return

        # Set the Stockfish path
        self.stockfish_path = f
        self.stockfish_path_text["text"] = self.stockfish_path
        self.stockfish_path_text.update()

    # Clears the Treeview
    def clear_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.tree.update()

    # Inserts a move into the Treeview
    def insert_move(self, move):
        # Get the total number of cells
        cells_num = sum(
            [len(self.tree.item(i)["values"]) - 1 for i in self.tree.get_children()]  # Get the number of childs
        )
        if (cells_num % 2) == 0:
            rows_num = len(self.tree.get_children())
            self.tree.insert("", "end", text="1", values=(rows_num + 1, move))
        else:
            self.tree.set(self.tree.get_children()[-1], column=2, value=move)
        self.tree.update()

    # Overwrites the Treeview with the given list of moves
    def set_moves(self, moves):
        self.clear_tree()
        self.match_moves = []

        # Insert in pairs
        pairs = list(zip(*[iter(moves)] * 2))
        for i, pair in enumerate(pairs):
            self.tree.insert("", "end", text="1", values=(str(i + 1), pair[0], pair[1]))

        # Insert the remaining one if it exists
        if len(moves) % 2 == 1:
            self.tree.insert("", "end", text="1", values=(len(pairs) + 1, moves[-1]))

        self.tree.update()

    def on_manual_mode_checkbox_listener(self):
        if self.enable_manual_mode.get() == 1:
            self.manual_mode_frame.pack(after=self.manual_mode_checkbox)
            self.manual_mode_frame.update()
        else:
            self.manual_mode_frame.pack_forget()
            self.manual_mode_checkbox.update()


if __name__ == "__main__":
    window = tk.Tk()
    my_gui = GUI(window)
    window.mainloop()
