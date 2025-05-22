# prefect_flows/schedules.py
from prefect import flow
from datetime import time
import subprocess

@flow(name="Fetch Product List Flow")
def fetch_product_list_flow():
    subprocess.run(["python", "fetch_product_list.py"], check=True)

@flow(name="Weekly Run Flow")
def run_weekly_flow():
    subprocess.run(["python", "run_weekly.py"], check=True)

@flow(name="Daily Post Scheduler Flow")
def master_scheduler_flow():
    subprocess.run(["python", "master_scheduler.py"], check=True)
