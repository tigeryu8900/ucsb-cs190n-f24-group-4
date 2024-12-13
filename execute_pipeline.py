import os
import time
from typing import Union

from netunicorn.base import Pipeline, ExperimentExecutionInformation, Experiment, DockerImage, ExperimentStatus, \
    Architecture
from netunicorn.client.remote import RemoteClientException, RemoteClient

netunicorn_login = 'cs190n4'
netunicorn_password = 'zvL89JkW'

NETUNICORN_ENDPOINT = os.environ.get('NETUNICORN_ENDPOINT', 'https://pinot.cs.ucsb.edu/netunicorn')
NETUNICORN_LOGIN = os.environ.get('NETUNICORN_LOGIN', netunicorn_login)
NETUNICORN_PASSWORD = os.environ.get('NETUNICORN_PASSWORD', netunicorn_password)

client = RemoteClient(endpoint=NETUNICORN_ENDPOINT, login=NETUNICORN_LOGIN, password=NETUNICORN_PASSWORD)
nodes = client.get_nodes()
# for pool in nodes:
#     for node in pool:
#         node.architecture = Architecture.LINUX_ARM64

def healthcheck():
    print("Health Check: {}".format(client.healthcheck()))
    print(nodes)


def execute_pipeline(
        pipelines: Union[Pipeline, list[Pipeline]],
        working_node: str,
        experiment_label: str
) -> ExperimentExecutionInformation:
    experiment = Experiment()

    for pipeline in pipelines:
        working_nodes = nodes.filter(lambda node: node.name.startswith(working_node)).take(1)
        experiment.map(pipeline, working_nodes)

    for deployment in experiment:
        deployment.environment_definition.commands = list(dict.fromkeys(deployment.environment_definition.commands))
        print("deployment executor_id:", deployment.executor_id)
        print("commands:")
        print('\n'.join(deployment.environment_definition.commands))
        print()
        # you can explore the image on the DockerHub
        # deployment.environment_definition = DockerImage(image="speeeday/chromium-speedtest:0.3.1")


    try:
        client.delete_experiment(experiment_label)
    except RemoteClientException:
        pass

    # Prepare Experiment
    client.prepare_experiment(experiment, experiment_label)
    while True:
        info = client.get_experiment_status(experiment_label)
        print(info.status)
        if info.status == ExperimentStatus.READY:
            break
        time.sleep(20)

    time.sleep(5)

    # Execute Experiment
    client.start_execution(experiment_label)
    while True:
        info = client.get_experiment_status(experiment_label)
        print(info.status)
        if info.status != ExperimentStatus.RUNNING:
            break
        time.sleep(20)
    return info


if __name__ == '__main__':
    healthcheck()
    # info = client.get_experiment_status("team-4-experiment-3")
    # print(info)

