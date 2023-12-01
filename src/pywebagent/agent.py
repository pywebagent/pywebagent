import base64
from enum import Enum
import json
import time
import logging
from pywebagent.env.browser import BrowserEnv
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI

logger = logging.getLogger(__name__)


TASK_STATUS = Enum("TASK_STATUS", "IN_PROGRESS SUCCESS FAILED")

class Task:
    def __init__(self, task, args) -> None:
        self.task = task
        self.args = args

def get_llm():
    return ChatOpenAI(
        model_name="gpt-4-vision-preview",
        temperature=1, 
        request_timeout=120, 
        max_tokens=2000,
    )

def generate_user_message(task, observation):
    log_history = '\n'.join(observation.log_history if observation.log_history else [])
    text_prompt = f"""
        Execution error: 
        {observation.error_message}

        URL: 
        {observation.url}
        
        Task: 
        {task.task}

        Log of last actions:
        {log_history}

        Task Arguments:
        {json.dumps(task.args, indent=4)}
        
    """

    screenshot_binary = observation.screenshot
    base64_image = base64.b64encode(screenshot_binary).decode('utf-8')
    image_content = {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}",
            "detail": "high", # low, high or auto
        },
    }
    text_content = {"type": "text", "text": text_prompt}
        
    return HumanMessage(content=[text_content, image_content])


def generate_system_message():
    system_prompt = """
    You are an AI agent that controls a webpage using python code, in order to achieve a task.
    You are provided a screenshot of the webpage at each timeframe, and you decide on the next python line to execute.
    You can use the following functions:
    - actions.click(element_id, log_message) # click on an element
    - actions.input_text(element_id, text, clear_before_input, log_message) # Use clear_before_input=True to replace the text instead of appending to it. Never use this method on a combobox.
    - actions.upload_files(element_id, files: list, log_message) # use this instead of click if clicking is expected to open a file picker
    - actions.combobox_select(element_id, option, log_message) # select an option from a combobox.
    - actions.finish(did_succeed, reason) # the task is complete with did_succeed=True or False, and a text reason

    element_id is always an integer, and is visible as a green label with white number inside the top-left corner of the element. Make sure to examine all green highlighted elements before choosing one to interact with.
    log_message is a short one sentence explanation of what the action does.
    Do not use keyword arguments, all arguments are positional.

    
    IMPORTANT: ONLY ONE WEBPAGE FUNCTION CALL IS ALLOWED, EXCEPT FOR FORMS WHERE MULTIPLE CALLS ARE ALLOWED TO FILL MULTIPLE FIELDS! NOTHING IS ALLOWED AFTER THE "```" ENDING THE CODE BLOCK
    IMPORTANT: LOOK FOR CUES IN THE SCREENSHOTS TO SEE WHAT PARTS OF THE TASK ARE COMPLETED AND WHAT PARTS ARE NOT. FOR EXAMPLE, IF YOU ARE ASKED TO BUY A PRODUCT, LOOK FOR CUES THAT THE PRODUCT IS IN THE CART.
    Response format:

    Reasoning:
    Explanation for the next action, particularly focusing on interpreting the attached screenshot image.

    Code:
    ```python
    # variable definitions and non-webpage function calls are allowed
    ...
    # a single webpage function call. 
    actions.func_name(args..)
    ```
    """
    return SystemMessage(content=system_prompt)


def extract_code(text):
    """
    Extracts all text in a string following the pattern "'\nCode:\n".
    """
    pattern = "\nCode:\n```python\n"
    start_index = text.find(pattern)
    if start_index == -1:
        raise Exception("Code not found")
    
    # Extract the text following the pattern, without the trailing "```"
    extracted_text = text[start_index + len(pattern):-3] 

    return extracted_text

def calcualte_next_action(task, observation):
    llm = get_llm()

    system_message = generate_system_message()
    user_message = generate_user_message(task, observation)

    try:
        ai_message = llm([system_message, user_message])
    except:
        # This sometimes solves the RPM limit issue
        logger.warning("Failed to get response from OpenAI, trying again in 30 seconds")
        time.sleep(30)
        ai_message = llm([system_message, user_message])
        
    logger.info(f"AI message: {ai_message.content}")

    code_to_execute = extract_code(ai_message.content)

    return code_to_execute
    
def get_task_status(observation):
    if observation.has_successfully_completed:
        return TASK_STATUS.SUCCESS
    elif observation.has_failed:
        return TASK_STATUS.FAILED
    else:
        return TASK_STATUS.IN_PROGRESS

def act(url, task, max_actions=40, **kwargs):
    task = Task(task=task, args=kwargs)

    browser = BrowserEnv(headless=False)

    observation = browser.reset(url)

    for i in range(max_actions):
        action = calcualte_next_action(task, observation) 
        observation = browser.step(action, observation.marked_elements)
        task_status = get_task_status(observation)
        if task_status in [TASK_STATUS.SUCCESS, TASK_STATUS.FAILED]:
            return task_status
    
    logger.warning(f"Reached {i} actions without completing the task.")
    return TASK_STATUS.FAILED

