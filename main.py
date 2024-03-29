# to start the controller
# to start the workload - read job from job queue
import sys
import time
import middleware
from LocalController import PIDController
from GlobalController import GlobalPIDController
import monitor
import logging
import os

import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='logfile.log')

def log_info(message):
    logging.info(message)

def log_error(message):
    logging.error(message)

def log_debug(message):
    logging.debug(message)

node_map = {
    1: "node1.group5project.ufl-eel6871-fa23-pg0.utah.cloudlab.us",
    2: "node2.group5project.ufl-eel6871-fa23-pg0.utah.cloudlab.us"
}

def parse_args(job):
    elements = job.split()
    pairs = [(elements[i], elements[i + 1]) for i in range(1, len(elements), 2)]
    formatted_output = ', '.join(f'"{key}", "{value}"' for key, value in pairs)
    return formatted_output


if __name__ == '__main__':
    args = sys.argv
    input_file = args[1]
    log_info("Job Files:" + str(input_file))
    with open(input_file, 'r') as f:
        jobs = f.readlines()
        log_info("Successfully Read Job Files")

    global_controller = GlobalPIDController(0)

    total_nodes = 2
    log_info("total_nodes = "+ str(total_nodes))
    local_controller_store = []
    for node in range(total_nodes):
        controller_instance = PIDController(0)
        local_controller_store.append(controller_instance)
    
    log_info("local_controller_store:"+str(local_controller_store))

    job_id = 0

    while True:
        cpu = monitor.get_cluster_utilization()
        if cpu:
            global_controller.update_utilization(cpu)
            global_controller.run_controller()
            nodes = int(global_controller.get_number_of_nodes())
            print("number of nodes: ", nodes)
            monitor_get_active_pods = monitor.get_active_pods()
            print("active pods: ", monitor.get_active_pods())
            log_info("number of nodes: " + str(nodes))
            log_info("active pods: " +  str(monitor_get_active_pods))
            if not monitor.is_node_active(node_map[1]) and not monitor.is_node_active(node_map[2]):
                print("Stop jobs, no nodes available")
                # sleep for 5 mins
                print("respawning")

                log_info("Stop jobs, no nodes available")
                log_info("respawning")
                
                middleware.restart_node(1)
                middleware.restart_node(2)
                time.sleep(300)
                # exit(0)

            for node in range(nodes):
                local_controller = local_controller_store[node]
                curr_node = node+1
                # avoid assigning jobs to dead node
                # check if node dead here
                node_name = node_map[curr_node]
                if curr_node==1 and not monitor.is_node_active(node_name):
                    curr_node = 2
                    log_info("curr_node"+str(curr_node))
                elif curr_node==2 and not monitor.is_node_active(node_name):
                    curr_node = 1
                    log_info("curr_node"+str(curr_node))
                if cpu>0.8:
                    middleware.kill_node(curr_node)
                    log_info("kill node"+str(curr_node))
                    global_controller.kill_node(curr_node)
                    log_info("global controller kill node"+str(curr_node))
                    curr_node = global_controller.get_node()
                if nodes==1:
                    curr_node = global_controller.get_node()
                local_cpu = monitor.get_node_cpu_utilization(curr_node)
                if local_cpu:
                    local_controller.update_utilization(local_cpu)
                    local_controller.run_controller()
                    pods = int(local_controller.get_number_of_pods())
                    print("node: ", curr_node)
                    print("number of pods: ", pods)
                    log_info("node:"+str(curr_node))
                    log_info("number of nodes" + str(pods))


                    if job_id >= len(jobs):
                        log_info("node exit")
                        exit(0)

                    if pods > len(jobs):
                        for job in jobs:
                            print("on job id: ", job_id)
                            log_info("on job id"+str(job_id))
                            if job_id >= len(jobs):
                                break
                            job = job.strip()
                            # i/p example stress-ng --io 4 --vm 5 --vm-bytes 2G --timeout 5m
                            # o/p example "--io", "4", "--vm", "5", "--vm-bytes", "2G", "--timeout", "5m"
                            formatted_output = parse_args(job)
                            # start pod on curr_node
                            middleware.start_pod(formatted_output, curr_node)
                            log_info("start new pods"+str(curr_node))
                            time.sleep(15) # process jobs after every 15s
                            local_cpu = monitor.get_node_cpu_utilization(curr_node)
                            if local_cpu:
                                print("cpu util for node ", curr_node, " is ", local_cpu)
                                log_info("cpu util for node"+str(curr_node)+"is"+str(local_cpu))
                                if local_cpu>0.8:
                                    break
                            job_id+=1
                    else:
                        count=0
                        while job_id < len(jobs):
                            print("on job id: ", job_id)
                            if job_id >= len(jobs):
                                break
                            if pods==count:
                                break
                            job = jobs[job_id]
                            job = job.strip()
                            formatted_output = parse_args(job)
                            # start pod on curr_node
                            middleware.start_pod(formatted_output, curr_node)
                            log_info("start new pods"+str(curr_node))
                            time.sleep(15) # process jobs after every 15s
                            local_cpu = monitor.get_node_cpu_utilization(curr_node)
                            if local_cpu:
                                print("cpu util for node ", curr_node, " is ", local_cpu)
                                log_info("cpu util for node"+str(curr_node)+"is"+str(local_cpu))
                                if local_cpu>0.8:
                                    break
                            count+=1
                            job_id+=1
                    
