import ansible_runner
import json
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, Response

app = Flask(__name__)

# Define Prometheus metrics
disk_usage_gauge = Gauge('disk_usage_percent', 'Disk usage percentage', ['filesystem'])
cpu_load_gauge = Gauge('cpu_load', 'CPU Load Average', ['load_type'])
memory_usage_gauge = Gauge('memory_usage_mb', 'Memory usage in MB', ['type'])

def run_ansible():
    """Runs the Ansible playbook and returns the result."""
    runner = ansible_runner.run(
        private_data_dir='.',  # Set this to the directory containing your playbook
        playbook='gather_stats.yml',  # Your playbook file
        inventory='hosts.ini',  # Your inventory file
    )

    # Parse the JSON result
    return json.loads(runner.stdout)

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
    app.run(host='0.0.0.0', port=8000)
