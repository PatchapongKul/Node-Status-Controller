import subprocess
from dotenv import load_dotenv
import os
import requests
import logging
from time import sleep

# Configure logging
logging.basicConfig(
    filename='./record/system_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from ".env"
load_dotenv()
BMC_CILLIUM3 = os.environ.get('BMC_CILLIUM3')
BMC_CILLIUM4 = os.environ.get('BMC_CILLIUM4')
IPMI_CILLIUM3 = os.environ.get('IPMI_CILLIUM3')
IPMI_CILLIUM4 = os.environ.get('IPMI_CILLIUM4')
IPMI_USERNAME = os.environ.get('IPMI_USERNAME')
CLEANUP_URL = os.environ.get('CLEANUP_URL')

def generate_cmd(action):
    if action == 0: 
        return None, None, None

    # Determine the BMC and IPMI values
    if action in [1, 2]:
        BMC = BMC_CILLIUM3
        IPMI = IPMI_CILLIUM3
        node = 'cillium3'
    else:
        BMC = BMC_CILLIUM4
        IPMI = IPMI_CILLIUM4
        node = 'cillium4'
    # Determine the command
    CMD = "on" if action in [1, 3] else "off"

    # Construct and return the command
    command = [
        "ipmitool",
        "-I", "lanplus",
        "-H", BMC,
        "-U", IPMI_USERNAME,
        "-P", IPMI,
        "chassis", "power", CMD
    ]

    return command, node, CMD

def run_action(action_choice):
    command, node, CMD = generate_cmd(action_choice)

    if command is None:
        return
    
    try:
        if CMD == "on":
            response = requests.post(CLEANUP_URL + '/uncordon', json={'node_name': node})
            logging.info(f"Uncordon node {node}: {response.json()}")
        elif CMD == "off":
            response = requests.post(CLEANUP_URL + '/drain', json={'node_name': node})
            logging.info(f"Draining node {node}: {response.json()}")
        sleep(90)
    except:
        logging.error("Error Drain or Uncordon node")
        
    logging.info(f"Running command: {' '.join(command)}")
    try:
        # Run the command
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        logging.info("Command output: %s", result.stdout)
        return
        
    except FileNotFoundError:
        logging.error("Error: 'ipmitool' not found. Please ensure it is installed and in your PATH.")
        return
    except subprocess.CalledProcessError as e:
        logging.error("Error executing command:")
        logging.error("Command: %s", ' '.join(e.cmd))
        logging.error("Return code: %d", e.returncode)
        logging.error("Output: %s", e.output.decode() if e.output else 'No output')
        logging.error("Error: %s", e.stderr.decode() if e.stderr else 'No error message')
        return

    