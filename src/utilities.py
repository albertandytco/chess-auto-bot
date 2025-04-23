from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver import Remote


# Constant for the base character for the conversion
BASE_CHAR = "a"


# Converts a chess character into an int
# Examples: a -> 1, b -> 2, h -> 8, etc.
def char_to_num(char):
    """Converts a chess column character to its corresponding numerical index (1-8).

    Args:
        char (str): The chess column character (e.g., 'a', 'b', 'h').

    Returns:
        int: The numerical index of the column (1-8).
    """
    return ord(char) - ord(BASE_CHAR) + 1


# Attaches to a running webdriver
def attach_to_session(executor_url, session_id):
    """Attaches to an existing Selenium WebDriver session.

    This function allows re-attaching to an existing browser session
    using its executor URL and session ID. It patches the WebDriver.execute
    method to mock the 'newSession' command response.

    Args:
        executor_url (str): The URL of the WebDriver's remote executor.
        session_id (str): The ID of the existing WebDriver session.

    Returns:
        WebDriver: A WebDriver instance attached to the existing session.

    Raises:
        Exception: If unable to attach to the session.
    """
    original_execute = WebDriver.execute  # Store the original WebDriver.execute method

    def new_command_execute(self, command, params=None):
        if command == "newSession":  # If the command is "newSession", mock the response
            return {"success": 0, "value": None, "sessionId": session_id}  # Mock response
        return original_execute(self, command, params)  # For other commands, use the original method

    WebDriver.execute = new_command_execute  # Patch the WebDriver.execute method
    driver = Remote(command_executor=executor_url, desired_capabilities={})  # Create a Remote instance
    driver.session_id = session_id  # Set the session ID
    WebDriver.execute = original_execute  # Restore the original WebDriver.execute method

    return driver  # Return the attached driver
