#!../../../../datadir_local/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# transit_search_worker_v2.py

"""
Run speed tests as requested through the RabbitMQ message queue

See:
https://stackoverflow.com/questions/14572020/handling-long-running-tasks-in-pika-rabbitmq/52951933#52951933
https://github.com/pika/pika/blob/0.12.0/examples/basic_consumer_threaded.py
"""

import argparse
import logging
import os
import functools
import json

import pika
from plato_wp36 import settings, task_runner


def acknowledge_message(channel, delivery_tag):
    """
    Acknowledge receipt of a RabbitMQ message, thereby preventing it from being sent to other worker nodes.
    """
    channel.basic_ack(delivery_tag=delivery_tag)


def do_work(connection=None, channel=None, delivery_tag=None, body="[{'task':'null'}]"):
    """
    Perform a list of tasks sent to us via a RabbitMQ message
    """
    # Extract list of the jobs we are to do
    task_list = json.loads(body)

    # Do each task in list
    task_runner.do_work(task_list=task_list)

    # Acknowledge the message we've just processed
    if connection is not None:
        cb = functools.partial(acknowledge_message, channel, delivery_tag)
        connection.add_callback_threadsafe(cb)


def receive(broker="amqp://guest:guest@rabbitmq-service:5672", queue="tasks"):
    """
    A very simple RabbitMQ consumer, which receives a simple task from the job queue, acknowledges it, and then
    closes the connection to RabbitMQ. This workflow prevents issues with the RabbitMQ connection dropping during
    long-running transit-search tasks.
    """
    connection = pika.BlockingConnection(pika.URLParameters(url=broker))
    channel = connection.channel()
    channel.queue_declare(queue=queue)
    method_frame, header_frame, body = channel.basic_get(queue=queue)
    if method_frame is None or method_frame.NAME == 'Basic.GetEmpty':
        connection.close()
        return None
    else:
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        connection.close()
        return body


def run_transit_searches(broker="amqp://guest:guest@rabbitmq-service:5672", queue="tasks"):
    """
    Set up a very simple RabbitMQ consumer to receive messages from the job queue, one by one
    """
    logging.info('Waiting for messages. To exit press CTRL+C')
    while True:
        # Fetch next message from queue
        message = receive(broker=broker, queue=queue)

        # If no message received quit
        if message is None:
            return

        # Run requested job
        do_work(body=message)


if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()

    # Set up logging
    log_file_path = os.path.join(settings.settings['dataPath'], 'plato_wp36.log')
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(log_file_path),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    # Enter infinite loop of listening for RabbitMQ messages telling us to do work
    run_transit_searches()
