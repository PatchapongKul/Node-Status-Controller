import requests
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(
    filename='./record/system_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from ".env"
load_dotenv()
PROMETHEUS_URL = os.environ.get('PROMETHEUS_URL')

def extract_and_format_values(data, no_nodes=4, no_start=1):
    # Initialize a dictionary with default values for cillium1 to cillium4
    values_dict = {f'cillium{i}': -1 for i in range(no_start, no_start+no_nodes)}
    # Extract values from the data
    for item in data:
        node = item['metric']['node']
        value = float(item['value'][1])
        values_dict[node] = value

    # Sort the keys and format the values to two decimal places
    sorted_keys = sorted(values_dict.keys(), key=lambda x: int(x.replace('cillium', '')))
    formatted_values = [round(values_dict[key], 2) for key in sorted_keys]

    return formatted_values

def get_number_data(data):
    if len(data) == 0: return [0]
    else: return [int(data[0]['value'][1])]

# Get state from the cluster
def get_current_state():
    try:
        # Default parameters
        active_node_status = 0

        # Query CPU Utilization
        cpu_usage_percentage = '100 - (avg by (node) (rate(node_cpu_seconds_total{mode="idle"}[15s])) * 100)'
        cpu_usage_percentage_response = requests.get(PROMETHEUS_URL, params={'query': cpu_usage_percentage}).json()
        cpu_usage_percentage_json = {result['metric']['node']: round(float(result['value'][1]),2) for result in cpu_usage_percentage_response['data']['result']}
        CPU_usage = extract_and_format_values(cpu_usage_percentage_response['data']['result'])
        
        # Active node list
        active_node_list = list(cpu_usage_percentage_json.keys())
        if 'cillium3' in active_node_list:
            active_node_status += 2
        if 'cillium4' in active_node_list:
            active_node_status += 1
        print('active_node_status:', active_node_status)
        
        # Query Memory Utilization
        mem_usage_percentage = '100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)'
        mem_usage_percentage_response = requests.get(PROMETHEUS_URL, params={'query': mem_usage_percentage}).json()
        MEM_usage = extract_and_format_values(mem_usage_percentage_response['data']['result'])

        # GPU Utilization
        gpu_usage_percentage = 'sum by (node) (DCGM_FI_DEV_GPU_UTIL)'
        gpu_usage_percentage_response = requests.get(PROMETHEUS_URL, params={'query': gpu_usage_percentage}).json()
        GPU_usage = extract_and_format_values(gpu_usage_percentage_response['data']['result'],2,3)

        # GPU Temperature
        gpu_temp = 'sum by (node) (DCGM_FI_DEV_GPU_TEMP)'
        gpu_temp_response = requests.get(PROMETHEUS_URL, params={'query': gpu_temp}).json()
        GPU_temp = extract_and_format_values(gpu_temp_response['data']['result'],2,3)

        # Number of completed batch jobs
        completed_batch_job = 'sum(kube_pod_status_phase{phase="Succeeded",namespace="batch-job"})'
        completed_batch_job_response = requests.get(PROMETHEUS_URL, params={'query': completed_batch_job}).json()
        completed_batch_job = get_number_data(completed_batch_job_response['data']['result'])

        # Number of completed batch jobs
        running_batch_job = 'sum(kube_pod_status_phase{phase="Running",namespace="batch-job"})'
        running_batch_job_response = requests.get(PROMETHEUS_URL, params={'query': running_batch_job}).json()
        running_batch_job = get_number_data(running_batch_job_response['data']['result'])

        # Number of total assigned batch jobs
        total_batch_job = 'count by (created_by_name) (kube_pod_info{namespace="batch-job"})'
        total_batch_job_response = requests.get(PROMETHEUS_URL, params={'query': total_batch_job}).json()
        total_batch_job = get_number_data(total_batch_job_response['data']['result'])

        # Number of pending batch jobs
        pending_batch_job = 'sum(kube_pod_status_phase{phase="Pending", namespace="batch-job"})'
        pending_batch_job_response = requests.get(PROMETHEUS_URL, params={'query': pending_batch_job}).json()
        pending_batch_job = get_number_data(pending_batch_job_response['data']['result'])

        # Number of gpu-job job
        long_runnning_job = 'sum(kube_pod_status_phase{phase="Running", namespace="gpu-job"})'
        long_runnning_job_response = requests.get(PROMETHEUS_URL, params={'query': long_runnning_job}).json()
        long_runnning_job = get_number_data(long_runnning_job_response['data']['result'])

        # Number of pending gpu-job jobs
        pending_gpu_job_job = 'sum(kube_pod_status_phase{phase="Pending", namespace="gpu-job"})'
        pending_gpu_job_job_response = requests.get(PROMETHEUS_URL, params={'query': pending_gpu_job_job}).json()
        pending_gpu_job_job = get_number_data(pending_gpu_job_job_response['data']['result'])

        return [active_node_status] + CPU_usage + MEM_usage + GPU_usage + GPU_temp + completed_batch_job + running_batch_job + pending_batch_job + total_batch_job + long_runnning_job + pending_gpu_job_job

    except:
        logging.error("Error querying from Prometheus")

def get_average_value():
    try:
        average = dict()
        state = get_current_state()
        average['state'] = state[0]
        cpu_usage_worker = [usage for usage in state[2:5] if usage != -1]
        # mem_usage_worker = [usage for usage in state[6:9] if usage != -1]
        average["num_worker"] = len(cpu_usage_worker)
        if average["num_worker"] == 0:
            average["cpu_worker"] = 100
            # average["mem_worker"] = 100
        else: 
            average["cpu_worker"] = sum(cpu_usage_worker)/len(cpu_usage_worker)
            # average["mem_worker"] = sum(mem_usage_worker)/len(mem_usage_worker)
        
        gpu_usage_worker = [usage for usage in state[9:11] if usage != -1]
        if len(gpu_usage_worker) > 0:
            average["gpu_worker"] = sum(gpu_usage_worker)/len(gpu_usage_worker)
        else:
            average["gpu_worker"] = -1
        return average, state
    
    except:
        logging.error("Error computing average values")