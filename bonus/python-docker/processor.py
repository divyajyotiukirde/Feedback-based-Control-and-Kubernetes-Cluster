import middleware
from LocalController import PIDController
from collections import deque
import monitor
import time


node_map = {
    1: "node1.group5project.ufl-eel6871-fa23-pg0.utah.cloudlab.us",
    2: "node2.group5project.ufl-eel6871-fa23-pg0.utah.cloudlab.us"
}

class JobScheduler():
    def __init__( self ):
        self.job_queue = deque()
        self.job_id = 0

        self.cluster_cpu = 0
        self.node_cpu = []

        self.local_controller_store = []
        total_nodes = 2
        for _ in range(total_nodes):
            controller_instance = PIDController(0)
            self.local_controller_store.append(controller_instance)

        self.is_processing = False

    def update_cpu(self, cpu_str):
        if len(cpu_str):
            cpu = cpu_str.split(',')
            if len(cpu)>=2:
                self.cluster_cpu = float(cpu[0])
                self.node_cpu = cpu[1:]

    def add_in_queue(self,job):
        self.job_queue.append(job)

    def is_queue_empty(self):
        return True if len(self.job_queue)==0 else False

    def process_queue(self):
        if self.is_processing==True:
            return
        self.is_processing = True
        while len(self.job_queue):
            cpu = monitor.get_cluster_utilization()
            if cpu:
                curr_node = 1

                if not monitor.is_node_active(node_map[1]) and not monitor.is_node_active(node_map[2]):
                    print("Stop jobs, no nodes available")
                    # sleep for 5 mins
                    print("respawning")
                    
                    middleware.restart_node(1)
                    middleware.restart_node(2)

                if cpu>0.8:
                    middleware.kill_node(curr_node)
                    print("kill node"+str(curr_node))
                    #print("global controller kill node"+str(curr_node))
                    curr_node = 2
                local_controller = self.local_controller_store[curr_node-1]

                local_cpu = monitor.get_node_cpu_utilization(curr_node)
                if local_cpu:
                    local_controller.update_utilization(local_cpu)
                    local_controller.run_controller()
                    pods = int(local_controller.get_number_of_pods())
                    print("node: ", curr_node)
                    print("number of pods: ", pods)

                    if pods > len(self.job_queue):
                        for job in self.job_queue:
                            job = job.strip()
                            # i/p example stress-ng --io 4 --vm 5 --vm-bytes 2G --timeout 5m
                            # o/p example "--io", "4", "--vm", "5", "--vm-bytes", "2G", "--timeout", "5m"
                            # start pod on curr_node
                            middleware.start_pod(job, curr_node)
                            if local_cpu:
                                print("cpu util for node ", curr_node, " is ", local_cpu)
                                #print("cpu util for node"+str(curr_node)+"is"+str(local_cpu))
                                if local_cpu>0.8:
                                    break
                            self.job_id+=1
                            time.sleep(15)
                    else:
                        count=0
                        while self.job_id < len(self.job_queue):
                            if pods==count:
                                break
                            job = self.job_queue[self.job_id]
                            job = job.strip()
                            # start pod on curr_node
                            middleware.start_pod(job, curr_node)
                            if local_cpu:
                                print("cpu util for node ", curr_node, " is ", local_cpu)
                                #print("cpu util for node"+str(curr_node)+"is"+str(local_cpu))
                                if local_cpu>0.8:
                                    break
                            count+=1
                            self.job_id+=1
                            time.sleep(15)
                    if curr_node==2 and pods>2:
                        self.is_processing = False
                        exit(0)
        self.is_processing = False
