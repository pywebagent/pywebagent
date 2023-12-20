import os
from pathlib import Path
import traceback
import time
import logging
from dataclasses import dataclass
from typing import Any, Tuple, Dict
from playwright.sync_api import sync_playwright
from pywebagent.env.actions import Actions, EnvState

logger = logging.getLogger(__name__)

JS_DIRECTORY = Path(os.path.dirname(os.path.realpath(__file__))) / "../js"


@dataclass
class WebpageObservation:
    url: str
    error_message: str
    screenshot: bytes
    marked_elements: Dict[str, Any]
    env_state: EnvState = None


class BrowserEnv:
    def __init__(self, headless: bool = True):
        # headless = 'new' if headless else False TODO make this work
        self.context_manager = sync_playwright()
        self.playwright = self.context_manager.__enter__()
        self.browser = self.playwright.chromium.launch(
            channel="chrome",
            headless=headless,
        )

        with open(JS_DIRECTORY / "mark_borders.js", 'r') as file:
            self._mark_elements_js_script = file.read()
        with open(JS_DIRECTORY / "remove_mark_borders.js", 'r') as file:
            self.remove_elements_marks_js_script = file.read()
        with open(JS_DIRECTORY / "override_file_chooser.js", 'r') as file:
            self.override_file_chooser_js_script = file.read()
        
    def step(self, code: str, marked_elements: list = []) -> WebpageObservation:
        self.env_state.log_history = []  # Clear log history to have logs only for the current step
        actions = Actions(self.page, marked_elements, self.env_state)
        context = {"actions": actions}
        try:
            error_message = None
            logger.info(f"Executing code: {code}")
            exec(code, context, context)
        except Exception as e:
            # Extract exception line number and rethrow it with it
            _, _, exc_tb = traceback.sys.exc_info()
            line_of_code = "N/A"
            while exc_tb is not None:
                frame = exc_tb.tb_frame
                lineno = exc_tb.tb_lineno
                if frame.f_code.co_name == "<module>" and frame.f_code.co_filename == "<string>":
                    line_of_code = code.split('\n')[lineno - 1].lstrip()
                    break
                exc_tb = exc_tb.tb_next

            error_message = f"Error in execution of script. At line: \"{line_of_code}\". Error: \"{e}\""
            logger.warning(error_message)
        finally:
            self._remove_elements_marks()

        try:
            self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception as e:
            logger.warning(f"Exception while waiting for load state: {e}")

        self.env_state.timeframe += 1
        time.sleep(2)
        obs = self.get_observation()

        # if a new page was opened, switch to it
        if len(self.context.pages) > 1:
            self.page.close()
            self.page = self.context.pages[-1]
            try:
                self.page.wait_for_load_state("networkidle", timeout=5000)
            except Exception as e:
                logger.warning(f"Exception while waiting for load state: {e}")
            obs = self.get_observation()

        obs.error_message = error_message
        return obs
    
    def _mark_elements(self):
        def run_script_in_frame(frame, counter, iframe_name=None):
            # Modify the script to start with the specific counter
            modified_script = self._mark_elements_js_script.replace(
                'let counter = 0;', f'let counter = {counter};')

            try:
                elements = frame.evaluate(modified_script)
            except Exception as e:
                # log exception
                logger.warning(f"Exception while running script in frame {iframe_name}: {e}")
                elements = []

            # Add iframe origin information to each element
            for element in elements:
                element['iframe'] = frame
                element['iframe_name'] = iframe_name

            return elements

        counter = 0
        marked_elements = []
        for frame in self.page.frames:
            iframe_name = frame.name or frame.url  # Use the frame's name or URL as an identifier
            marked_elements_iframe = run_script_in_frame(frame, counter, iframe_name=iframe_name)
            marked_elements.extend(marked_elements_iframe)
            counter += len(marked_elements_iframe)

        marked_elements = {element['id']: element for element in marked_elements}
        return marked_elements
    
    def _remove_elements_marks(self):
        for frame in self.page.frames:
            try:
                frame.evaluate(self.remove_elements_marks_js_script)
            except Exception as e:
                logger.warning(f"Exception while running removal script in frame {frame.name}: {e}")
                if "Target closed" in str(e):
                    return 
    
    def get_observation(self) -> WebpageObservation:
        marked_elements = self._mark_elements()
        screenshot = self.page.screenshot()

        return WebpageObservation(
            url=self.page.url,
            error_message=None,
            screenshot=screenshot,
            marked_elements=marked_elements,
            env_state = self.env_state,
        )
        
    def reset(self, url) -> Tuple[WebpageObservation, Dict[str, Any]]:
        geolocation = {"longitude": -122.417168, "latitude": 37.785834}  # USA
        self.context = self.browser.new_context(
            viewport={"width": 1600, "height": 900},
            storage_state=None,
            geolocation=geolocation,
            device_scale_factor=1,
        )
        self.page = self.context.new_page()

        #  Overrides the standard file picker function in the browser with a custom implementation 
        # for file selection. This allows filechooser events to be triggered from the python code.
        self.page.add_init_script(self.override_file_chooser_js_script)

        self.page.goto(url)
        logger.info("Waiting for page to load...")
        try:
            self.page.wait_for_load_state("networkidle")
        except Exception as e:
            logger.warning(f"Exception while waiting for load state: {e}")
            # try to wait for "load" state, sometimes the page is stuck with network traffic loading
            self.page.wait_for_load_state("load")
        logger.info("Page loaded")
        self.env_state = EnvState()
        return self.get_observation()

    def close(self):
        self.context_manager.__exit__()
        self.browser.close()
