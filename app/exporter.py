import ansible_runner
import json
from prometheus_client import Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
from flask import Flask, Response
from icecream import ic
import os

app = Flask(__name__)

def run_ansible():
    runner = ansible_runner.run(
        private_data_dir='app',
        playbook='gather_stats.yaml',
        inventory='/home/user/home/Nextcloud2/dev/proxmox_stats/app/inventory.ini'
    )
    resultset = {}
    for event in runner.events:
        if "event_data" in event and "res" in event["event_data"]:
            if "usage_stats_output" in event["event_data"]["res"]:
              resultset[event["event_data"]["host"]]=event["event_data"]["res"]["usage_stats_output"]

    for host in runner.stats['processed']:
      ic(host)
      if not host in resultset:
        resultset[host]={}
      if not 'ansible' in resultset[host]:
        resultset[host]['ansible']={}
      resultset[host]['ansible']['ok']=runner.stats['ok'].get(host, 0)
      resultset[host]['ansible']['failures']=runner.stats['failures'].get(host, 0)
      resultset[host]['ansible']['dark']=runner.stats['dark'].get(host, 0)

    ic(runner.stats)

    ic(resultset)
    return resultset

def set_gauge(gauges, metrics_registry, host, values, prefix = ''):
  for key, value in values.items():
    if isinstance(value, dict):
      set_gauge(gauges, metrics_registry, host, value, key)
    else:
      key_id = key if not prefix else f'{prefix}_{key}'
      if key_id not in gauges:
        gauges[key_id] = Gauge(
          key_id,
          '',
          ['host'],
          registry=metrics_registry
        )
      print(f'{host}_{key_id} is {value}')
      gauges[key_id].labels(host=host).set(value)  

@app.route('/metrics')
def metrics():
    """Fetch system stats and update Prometheus metrics."""
    stats = run_ansible()
    if not stats:
        return

    metrics_registry = CollectorRegistry()
    gauges={}

    for host, values in stats.items():
      set_gauge(gauges, metrics_registry, host, values)

    return Response(generate_latest(metrics_registry), content_type=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
