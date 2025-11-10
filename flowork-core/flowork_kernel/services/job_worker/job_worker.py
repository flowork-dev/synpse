########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\job_worker\job_worker.py total lines 214 
########################################################################

import time
import os
import signal
import sys
import traceback
import json
import logging
from multiprocessing import Event
from flowork_kernel.services.database_service.database_service import DatabaseService
from flowork_kernel.services.module_manager_service.module_manager_service import ModuleManagerService
from flowork_kernel.services.gateway_connector_service.gateway_connector_service import GatewayConnectorService
from flowork_kernel.services.logging_service.logging_service import setup_logging
from flowork_kernel.services.prewarm_service.prewarm_service import prewarm_models # (Added for 4.3)
log = setup_logging(__name__, "job_worker.log")
JOB_DEADLINE_SECONDS = int(os.getenv("CORE_JOB_DEADLINE_SECONDS", "120")) # (From Roadmap 1.F)
def job_worker_process(job_event: Event, stop_event: Event):
    """
    This function runs in a separate process to execute jobs from the queue.
    """
    log.info(f"Job worker process started (PID: {os.getpid()}). Waiting for tasks.")
    db_service = DatabaseService()
    module_manager = ModuleManagerService()
    gateway_connector = GatewayConnectorService() # For progress updates
    signal.signal(signal.SIGINT, lambda s, f: stop_event.set())
    signal.signal(signal.SIGTERM, lambda s, f: stop_event.set())
    try:
        log.info(f"[Worker {os.getpid()}] Starting pre-warm sequence...")
        prewarm_models()
        log.info(f"[Worker {os.getpid()}] Pre-warm sequence finished. Starting job polling.")
    except Exception as e:
        log.error(f"[Worker {os.getpid()}] Pre-warm sequence FAILED: {e}. Starting poll anyway.")
    while not stop_event.is_set():
        job = None
        try:
            job_event.wait(timeout=2.0)
            if stop_event.is_set():
                break # (English Hardcode) Exit loop if stop is requested
            job_event.clear() # (English Hardcode) We'll handle the jobs
            job = _db_get_next_job(db_service)
            if job:
                log.info(f"Worker {os.getpid()} picked up job: {job['id']} (Node: {job['node_name']})")
                deadline = time.time() + JOB_DEADLINE_SECONDS
                output_data, status, error_message = execute_node_logic(
                    job,
                    module_manager,
                    gateway_connector,
                    deadline,
                    stop_event # (English Hardcode) Pass stop_event for deadline check
                )
                if status == "STOPPED" or status == "TIMED_OUT":
                    log.warning(f"Job {job['id']} was {status}. Marking as ERROR.")
                    _db_finish_job(db_service, job['id'], status, None, error_message, job['execution_id'])
                else:
                    log.info(f"Job {job['id']} finished with status: {status}")
                    _db_finish_job(db_service, job['id'], status, output_data, error_message, job['execution_id'])
                    if status == "DONE" and output_data is not None:
                        downstream_nodes = _db_get_downstream_nodes(db_service, job['node_id'], job['preset_id'])
                        if downstream_nodes:
                            log.info(f"Enqueuing {len(downstream_nodes)} downstream jobs for node {job['node_id']}")
                            for node_id, node_name, target_handle in downstream_nodes:
                                next_input = {target_handle: output_data.get("output")} # (FIX) Simplified input mapping
                                _db_enqueue_job(
                                    db_service,
                                    job['execution_id'],
                                    job['preset_id'],
                                    node_id,
                                    node_name,
                                    json.dumps(next_input), # (FIX) Pass output as input
                                    job_id # (English Hardcode) Pass parent job_id
                                )
                            job_event.set()
            else:
                pass
        except Exception as e:
            log.error(f"FATAL: Unhandled exception in job worker loop: {e}")
            log.error(traceback.format_exc())
            if job:
                log.error(f"Job {job['id']} may be stuck. Attempting to mark as ERROR.")
                try:
                    _db_finish_job(db_service, job['id'], "ERROR", None, str(e), job.get('execution_id', 'unknown'))
                except Exception as db_e:
                    log.error(f"Failed to mark job {job['id']} as ERROR: {db_e}")
            time.sleep(1.0)
    log.info(f"Job worker process (PID: {os.getpid()}) shutting down.")
def _db_get_next_job(db_service: DatabaseService) -> dict:
    try:
        job = db_service.execute_query(
            """
            UPDATE Jobs
            SET status = 'RUNNING', started_at = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT id
                FROM Jobs
                WHERE status = 'PENDING'
                ORDER BY created_at
                LIMIT 1
            )
            RETURNING id, execution_id, preset_id, node_id, node_name, inputs, parent_job_id;
            """,
            fetch_one=True
        )
        return job
    except Exception as e:
        log.error(f"DB Error getting next job: {e}")
        return None
def execute_node_logic(job: dict, module_manager: ModuleManagerService, gateway_connector: GatewayConnectorService, deadline: float, stop_event: Event):
    try:
        node_name = job['node_name']
        inputs = json.loads(job['inputs']) if job['inputs'] else {}
        module_instance = module_manager.get_instance(node_name)
        if module_instance is None:
            raise ValueError(f"Module '{node_name}' not found or failed to load.")
        context = {
            "job_id": job['id'],
            "execution_id": job['execution_id'],
            "deadline": deadline,
            "stop_event": stop_event,
            "gateway_connector": gateway_connector
        }
        output = module_instance.execute(inputs, context)
        if stop_event.is_set():
            return None, "STOPPED", "Job execution was manually stopped."
        if time.time() > deadline:
            return None, "TIMED_OUT", f"Job exceeded deadline of {JOB_DEADLINE_SECONDS}s."
        return output, "DONE", None
    except Exception as e:
        log.error(f"Job {job['id']} (Node: {job['node_name']}) failed during execution: {e}")
        log.error(traceback.format_exc())
        return None, "ERROR", str(e)
def _db_finish_job(db_service: DatabaseService, job_id: str, status: str, output_data: dict, error_message: str, execution_id: str):
    try:
        output_json = json.dumps(output_data) if output_data else None
        db_service.execute_query(
            """
            UPDATE Jobs
            SET status = ?, output = ?, error_message = ?, finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            params=(status, output_json, error_message, job_id),
            commit=True
        )
        if status == "DONE" or status == "ERROR":
            _check_and_finalize_execution(db_service, execution_id)
    except Exception as e:
        log.error(f"DB Error finishing job {job_id}: {e}")
def _db_enqueue_job(db_service: DatabaseService, execution_id: str, preset_id: str, node_id: str, node_name: str, inputs_json: str, parent_job_id: str):
    try:
        db_service.execute_query(
            """
            INSERT INTO Jobs (execution_id, preset_id, node_id, node_name, inputs, status, parent_job_id)
            VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
            """,
            params=(execution_id, preset_id, node_id, node_name, inputs_json, parent_job_id),
            commit=True
        )
    except Exception as e:
        log.error(f"DB Error enqueuing job for node {node_id}: {e}")
def _db_get_downstream_nodes(db_service: DatabaseService, source_node_id: str, preset_id: str) -> list:
    try:
        rows = db_service.execute_query(
            """
            SELECT e.target_node_id, n.node_name, e.target_handle
            FROM Edges e
            JOIN Nodes n ON e.target_node_id = n.id
            WHERE e.source_node_id = ? AND e.preset_id = ? AND n.preset_id = ?
            """,
            params=(source_node_id, preset_id, preset_id),
            fetch_all=True
        )
        return rows
    except Exception as e:
        log.error(f"DB Error getting downstream nodes for {source_node_id}: {e}")
        return []
def _check_and_finalize_execution(db_service: DatabaseService, execution_id: str):
    try:
        pending_jobs = db_service.execute_query(
            """
            SELECT COUNT(id)
            FROM Jobs
            WHERE execution_id = ? AND status IN ('PENDING', 'RUNNING')
            """,
            params=(execution_id,),
            fetch_one=True
        )
        if pending_jobs and pending_jobs[0] == 0:
            log.info(f"All jobs for execution {execution_id} are complete. Finalizing...")
            failed_jobs = db_service.execute_query(
                """
                SELECT COUNT(id)
                FROM Jobs
                WHERE execution_id = ? AND status = 'ERROR'
                """,
                params=(execution_id,),
                fetch_one=True
            )
            final_status = "ERROR" if (failed_jobs and failed_jobs[0] > 0) else "DONE"
            db_service.execute_query(
                """
                UPDATE Executions
                SET status = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                params=(final_status, execution_id),
                commit=True
            )
            log.info(f"Execution {execution_id} finalized with status: {final_status}")
    except Exception as e:
        log.error(f"DB Error finalizing execution {execution_id}: {e}")
