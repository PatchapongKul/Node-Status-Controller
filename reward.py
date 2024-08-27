import os
from dotenv import load_dotenv
import logging
import csv
from pysnmp.hlapi import SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, getCmd
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='./record/system_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from ".env"
load_dotenv()
PROMETHEUS_URL = os.environ.get('PROMETHEUS_URL')
CLEANUP_URL = os.environ.get('CLEANUP_URL')
COMMUNITY  = os.environ.get('COMMUNITY')
PDU_IP     = os.environ.get('PDU_IP')
POWER_OID  = os.environ.get('POWER_OID')
ENERGY_OID = os.environ.get('ENERGY_OID')

# Define the OID to description mapping
OID_TO_DESCRIPTION = {
    POWER_OID: 'Power',
    ENERGY_OID: 'Energy'
}

def snmp_get(target, community, oid, port=161):
    """
    Perform an SNMP GET operation.

    :param target: The target device IP address or hostname.
    :param community: The SNMP community string.
    :param oid: The OID to query.
    :param port: The SNMP port number (default is 161).
    :return: The result of the SNMP GET operation.
    """
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=0),  # mpModel=0 means SNMPv1, for SNMPv2 use mpModel=1
        UdpTransportTarget((target, port)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )

    error_indication, error_status, error_index, var_binds = next(iterator)

    if error_indication:
        print(f"Error: {error_indication}")
        return None
    elif error_status:
        print(f"Error: {error_status.prettyPrint()} at {error_index and var_binds[int(error_index) - 1][0] or '?'}")
        return None
    else:
        result = {}
        for var_bind in var_binds:
            oid_str = str(var_bind[0])
            description = OID_TO_DESCRIPTION[oid_str]
            result[description] = int(var_bind[1].prettyPrint())
            if description == 'Power':  result[description] *= 10
            if description == 'Energy': result[description] /= 10
        return result

def save_to_csv(timestamp, power_usage, filename='./record/power_estimation.csv'):
    """ Save monitor result to a CSV file """
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            # Write the header row based on keys from SAR
            writer.writerow(['timestamp', 'power_usage'])
        
        # Write the row with data values
        writer.writerow([timestamp, power_usage])

def gather_power_consumption_data(previous_predicted):
    try:
        # Actual power
        power_pdu = snmp_get(PDU_IP, COMMUNITY, POWER_OID)

        timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        save_to_csv(timestamp, power_pdu['Power'])
          
        return power_pdu['Power']
    
    except:
        logging.error("Error getting power consumption")
        return -1