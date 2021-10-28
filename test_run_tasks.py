from batch_containers import run_tasks
from batch_creation import user_config

# Some job parameters
POOL_NAME = "distinct-tasks-pool"
JOB_NAME = "distinct-tasks-job"

# Define the arguments your task needs
args1 = ["output_dir"] * 3
args2 = ["scenario1", "scenario2", "scenario3"]

# Map them together as needed to make a single list of tasks
tasks_list = list(
    map(
        lambda x, y: f"python main.py --log-iterations --log-path {x} --sim-name {y}",
        args1,
        args2,
    )
)

# Run the tasks
run_tasks(
    config_file=user_config,
    pool_name=POOL_NAME,
    job_name=JOB_NAME,
    task_to_run=tasks_list,
    num_tasks=len(tasks_list),
    low_pri_nodes=3,
    dedicated_nodes=0,
    vm_sku="Standard_a2_v2",
    log_iterations=True,
    wait_time=2,
)
