from time import sleep, time
from collections import deque
from state import get_average_value
from action import run_action
from reward import gather_power_consumption_data
import os, csv
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='./record/system_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize deques with a maximum length of 12
recent_exceed = deque(maxlen=12)
recent_gpu_exceed = deque(maxlen=12)
recent_gpu_unused = deque(maxlen=12)
recent_under = deque(maxlen=60)

# Constants
CHECK_INTERVAL = 5  # seconds between checks
ACTION_DELAY_INTERVAL = 600  # seconds to wait before allowing action again
LOG_INTERVAL = 600  # seconds between logs

# Timing for action delay and logging
next_action_time = time()
next_log_time = time()

def save_to_csv(state, filename='./record/state.csv'):
    """ Save monitor result to a CSV file """
    timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            # Write the header row based on keys from SAR
            writer.writerow(['timestamp', 'active_node_status', 'cpu_usage_cillium1','cpu_usage_cillium2','cpu_usage_cillium3','cpu_usage_cillium4'
                             ,'mem_usage_cillium1','mem_usage_cillium2','mem_usage_cillium3','mem_usage_cillium4','gpu_usage_cillium3','gpu_usage_cillium4'
                             ,'gpu_temp_cillium3','gpu_temp_cillium4','completed_batch_job', 'running_batch_job', 'pending_batch_job', 'total_batch_job'
                             ,'long_runnning_job', 'pending_long_running_job'])
        
        # Write the row with data values
        writer.writerow([timestamp] + state)

while True:
    # Get current status
    average_current_state, current_state = get_average_value()
    save_to_csv(current_state)
    
    # Update deques based on CPU usage
    recent_exceed.append(average_current_state['cpu_worker'] > 70)
    recent_gpu_exceed.append(current_state[-1] > 0)
    recent_gpu_unused.append(average_current_state['gpu_worker'] <= 0)
    recent_under.append(average_current_state['cpu_worker'] < 20)
    current_time = time()

    # Check if it's time to perform actions
    if current_time >= next_action_time:
        # Exceed 70% CPU Utilization 6 times within a minute
        if len(recent_exceed) == 12 and sum(recent_exceed) > 6:
            if average_current_state['state'] == 0:
                run_action(1)
            elif average_current_state['state'] == 1:
                run_action(1)
            elif average_current_state['state'] == 2:
                run_action(3)
            else:
                run_action(0)
            
            # Update action delay timer
            next_action_time = current_time + ACTION_DELAY_INTERVAL
        
        # GPU pod is waiting for running within a minute
        elif len(recent_gpu_exceed) == 12 and sum(recent_gpu_exceed) > 6:
            if average_current_state['state'] == 0:
                run_action(1)
            elif average_current_state['state'] == 1:
                run_action(1)
            elif average_current_state['state'] == 2:
                run_action(3)
            else:
                run_action(0)
            
            # Update action delay timer
            next_action_time = current_time + ACTION_DELAY_INTERVAL

        # Under 20% Utilization for 5 minute
        elif len(recent_under) == 60 and all(recent_under) and all(recent_gpu_unused):
            if average_current_state['state'] == 1:
                run_action(4)
            elif average_current_state['state'] == 2:
                run_action(2)
            elif average_current_state['state'] == 3:
                run_action(2)
            else:
                run_action(0)
            
            # Update action delay timer
            next_action_time = current_time + ACTION_DELAY_INTERVAL

    # Gather power consumption data
    actual_power = gather_power_consumption_data()

    # Check if it's time to log power data
    if current_time >= next_log_time:
        logging.info(f"Actual Power: {actual_power}")
        next_log_time = current_time + LOG_INTERVAL

    # Sleep for the check interval
    sleep(CHECK_INTERVAL)
