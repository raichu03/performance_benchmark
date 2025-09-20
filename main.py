import time
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import os
import uuid
import psycopg2

from db_manager import NoPoolManager, PoolManager, DB_CONFIG

def setup_database():
    """Check if the table exists."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_name = 'users'
        );
    """)
    if not cur.fetchone()[0]:
        print("Table 'users' does not exist. Creating...")
        cur.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        conn.commit()
    
    cur.close()
    conn.close()

def run_crud_tests(manager, num_data_points, num_workers):
    """Runs tests for each CRUD operation and returns a dictionary of results."""
    results = {}
    
    data_points = []
    for _ in range(num_data_points):
        username = f"user_{uuid.uuid4().hex[:10]}"
        email = f"{username}@test.com"
        data_points.append({'username': username, 'email': email})

    print(f"  > Running CREATE test for {num_data_points} users...")
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(manager.create_user, dp['username'], dp['email']) for dp in data_points]
        user_ids = [future.result() for future in futures]
    results['create'] = time.time() - start_time
    
    print(f"  > Running READ test for {num_data_points} users...")
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        executor.map(manager.read_user, user_ids)
    results['read'] = time.time() - start_time

    print(f"  > Running UPDATE test for {num_data_points} users...")
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        executor.map(manager.update_user, user_ids, [f"updated_{dp['email']}" for dp in data_points])
    results['update'] = time.time() - start_time

    print(f"  > Running DELETE test for {num_data_points} users...")
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        executor.map(manager.delete_user, user_ids)
    results['delete'] = time.time() - start_time
    
    return results

def generate_report(results_no_pool, results_pool, num_data_points):
    """Generates a bar chart from the test results."""
    operations = ['Create', 'Read', 'Update', 'Delete']
    
    total_no_pool = sum(results_no_pool.values())
    total_pool = sum(results_pool.values())
    
    print(f"\n--- Total Performance Comparison ({num_data_points} CRUD cycles) ---")
    print(f"  Without Pooling: {total_no_pool:.2f} seconds")
    print(f"  With Pooling: {total_pool:.2f} seconds")
    print(f"  Performance Gain: {((total_no_pool - total_pool) / total_no_pool) * 100:.2f}%")
    print("-" * 50)
    
    operations_with_total = operations + ['Total']
    
    fig, ax = plt.subplots(figsize=(12, 8))
    x = range(len(operations_with_total))
    bar_width = 0.35
    
    no_pool_data = [results_no_pool[op.lower()] for op in operations] + [total_no_pool]
    pool_data = [results_pool[op.lower()] for op in operations] + [total_pool]
    
    rects1 = ax.bar([i - bar_width/2 for i in x], no_pool_data, bar_width, label='Without Pooling', color='skyblue')
    rects2 = ax.bar([i + bar_width/2 for i in x], pool_data, bar_width, label='With Pooling', color='salmon')

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., 1.01 * height, f'{height:.2f}s', ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    autolabel(rects1)
    autolabel(rects2)

    ax.set_ylabel('Total Duration (Seconds)', fontsize=12)
    ax.set_title(f'Performance of CRUD Operations with/without Pooling ({num_data_points} Data Points)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(operations_with_total)
    ax.legend()
    
    plt.tight_layout()
    
    if not os.path.exists("reports"):
        os.makedirs("reports")
    plt.savefig("reports/crud_performance_comparison.png")
    print("\nPerformance chart saved to 'reports/crud_performance_comparison.png'")

if __name__ == "__main__":
    setup_database()
    
    NUM_DATA_POINTS = 1000
    NUM_WORKERS = 50
    
    print(f"\nRunning tests for {NUM_DATA_POINTS} data points and {NUM_WORKERS} workers...")
    
    print("\n--- Running without connection pooling ---")
    no_pool_manager = NoPoolManager()
    results_no_pool = run_crud_tests(no_pool_manager, NUM_DATA_POINTS, NUM_WORKERS)
    
    print("\n--- Running with connection pooling ---")
    pool_manager = PoolManager()
    results_pool = run_crud_tests(pool_manager, NUM_DATA_POINTS, NUM_WORKERS)
    pool_manager.close_pool()
    
    generate_report(results_no_pool, results_pool, NUM_DATA_POINTS)

    print(f"no pool results: \n{results_no_pool}")
    print(f"pool results: \n{results_pool}")
    
    print("\n🎉 Test complete. Check the 'reports' folder for the graph.")