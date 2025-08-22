"""
Timed execution wrapper for complete_workflow_example.py
Measures execution time for every major operation
"""
import time
import sys
import os
from datetime import datetime
from contextlib import contextmanager

# Fix encoding for Windows
if os.name == 'nt':
    try:
        os.system('chcp 65001 > nul')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Add examples to path
sys.path.append('examples')

@contextmanager
def timer(operation_name):
    """Context manager to time operations"""
    start_time = time.perf_counter()
    print(f"[TIMER] [{datetime.now().strftime('%H:%M:%S')}] Starting: {operation_name}")
    
    try:
        yield
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"[TIMER] [{datetime.now().strftime('%H:%M:%S')}] Completed: {operation_name} in {duration:.2f}s")
    except Exception as e:
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"[TIMER] [{datetime.now().strftime('%H:%M:%S')}] Failed: {operation_name} after {duration:.2f}s - {e}")
        raise

def main():
    print("="*80)
    print("TIMED COMPLETE WORKFLOW EXECUTION")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    total_start = time.perf_counter()
    
    try:
        # Import the workflow module
        with timer("Import complete_workflow_example module"):
            import complete_workflow_example
        
        # Execute the main workflow with timing
        with timer("Complete workflow execution"):
            complete_workflow_example.main()
            
    except Exception as e:
        print(f"[ERROR] Workflow execution failed: {e}")
        return False
    finally:
        total_end = time.perf_counter()
        total_duration = total_end - total_start
        
        print("\n" + "="*80)
        print("EXECUTION SUMMARY")
        print(f"Total execution time: {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)