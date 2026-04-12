"""
物流系统 - 每日数据统计 DAG
每天凌晨 1 点执行，统计前一天的数据
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# 默认参数
default_args = {
    'owner': 'logistics',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG 定义
dag = DAG(
    'logistics_daily_statistics',
    default_args=default_args,
    description='物流系统每日数据统计',
    schedule_interval='0 1 * * *',  # 每天凌晨 1 点
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['logistics', 'statistics', 'daily'],
)


def calculate_daily_orders(**context):
    """计算每日订单统计"""
    from datetime import date, timedelta
    yesterday = date.today() - timedelta(days=1)
    print(f"统计日期: {yesterday}")
    # TODO: 实际的统计逻辑
    return f"订单统计完成: {yesterday}"


def calculate_vehicle_utilization(**context):
    """计算车辆利用率"""
    print("计算车辆利用率...")
    # TODO: 实际的计算逻辑
    return "车辆利用率计算完成"


def generate_daily_report(**context):
    """生成每日报告"""
    print("生成每日报告...")
    # TODO: 实际的报告生成逻辑
    return "每日报告已生成"


# 任务定义
task1 = PythonOperator(
    task_id='calculate_daily_orders',
    python_callable=calculate_daily_orders,
    dag=dag,
)

task2 = PythonOperator(
    task_id='calculate_vehicle_utilization',
    python_callable=calculate_vehicle_utilization,
    dag=dag,
)

task3 = PythonOperator(
    task_id='generate_daily_report',
    python_callable=generate_daily_report,
    dag=dag,
)

# 任务依赖
task1 >> task2 >> task3
