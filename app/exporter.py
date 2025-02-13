import ansible_runner
import json
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, Response
from icecream import ic
import os

app = Flask(__name__)

# Define Prometheus metrics
disk_usage_gauge = Gauge('disk_usage_percent', 'Disk usage percentage', ['filesystem'])
cpu_load_gauge = Gauge('cpu_load', 'CPU Load Average', ['load_type'])
memory_usage_gauge = Gauge('memory_usage_mb', 'Memory usage in MB', ['type'])

def run_ansible():
    runner = ansible_runner.run(
        private_data_dir='app',
        playbook='gather_stats.yaml',
        inventory='/home/user/home/Nextcloud2/dev/proxmox_stats/app/inventory.ini'
    )
    return runner
    metrics = []
    
    for host, stats in runner.stats.items():
        for key, value in stats.items():
            metric_name = f"ansible_{key}"
            metrics.append(f"{metric_name}{{host=\"{host}\"}} {value}")

    ic(metrics)

    resultset = {}
    for event in runner.events:
        if "event_data" in event and "res" in event["event_data"]:
            if "usage_stats_output" in event["event_data"]["res"]:
              resultset[event["event_data"]["host"]]=event["event_data"]["res"]["usage_stats_output"]
              print(json.dumps(event["event_data"], indent=2))
    return {}

def update_metrics():
    """Fetch system stats and update Prometheus metrics."""
    stats = run_ansible()
    if not stats:
        return

    for host, data in stats.get('plays', [{}])[0].get('tasks', []):
        if 'stats' in data.get('hosts', {}).get(host, {}):
            metrics = data['hosts'][host]['stats']

            # Update disk usage
            for line in metrics['disk']:
                parts = line.split()
                if len(parts) == 2:
                    filesystem, usage = parts
                    disk_usage_gauge.labels(filesystem=filesystem).set(float(usage.strip('%')))

            # Update CPU load
            cpu_load = metrics['cpu'].split()
            for i, load in enumerate(['1m', '5m', '15m']):
                cpu_load_gauge.labels(load_type=load).set(float(cpu_load[i]))

            # Update Memory usage
            mem_parts = metrics['memory'].split(',')
            used, total = mem_parts[0].split('=')[1], mem_parts[1].split('=')[1]
            memory_usage_gauge.labels(type='used').set(float(used))
            memory_usage_gauge.labels(type='total').set(float(total))

@app.route('/metrics')
def metrics():
    """Endpoint for Prometheus to scrape metrics."""
    update_metrics()
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
