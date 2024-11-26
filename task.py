import json
from utils.logger import logger
import time
from validator import BotValidator

async def check_and_claim_task(api_client, extension_id):
    """Cek dan klaim task rewards"""
    validator = BotValidator()
    last_check = time.time()
    
    try:
        # Cek validasi sebelum memulai task
        if not await validator.periodic_check():
            return

        response = api_client.get('/mission/tasks')
        
        if response.ok:
            tasks = response.json().get('data', [])
            
            # Filter task yang bisa diklaim (status 1)
            claimable_tasks = [task for task in tasks if task.get('status') == 1]
            
            if claimable_tasks:
                logger(f"[{extension_id}] Menemukan {len(claimable_tasks)} task yang bisa diklaim", 'success')
                for task in claimable_tasks:
                    task_id = task.get('id') or task.get('_id')
                    if not task_id:
                        logger(f"[{extension_id}] Task tidak memiliki ID yang valid", 'error')
                        continue
                        
                    try:
                        claim_response = api_client.post(f"/mission/tasks/{task_id}/claim")
                        if claim_response.ok:
                            claim_data = claim_response.json()
                            logger(f"[{extension_id}] Reward diklaim: Task ID {task_id}", 'success')
                        else:
                            logger(f"[{extension_id}] Gagal klaim task {task_id}: {claim_response.json().get('message')}", 'warn')
                    except Exception as e:
                        logger(f"[{extension_id}] Error saat klaim task {task_id}: {str(e)}", 'error')
            else:
                logger(f"[{extension_id}] Tidak ada task yang bisa diklaim", 'info')
    except Exception as e:
        logger(f"[{extension_id}] Error saat check task: {str(e)}", 'error')
