# -*- coding: utf-8 -*-
# results_logger.py

import json
import pika
import logging

from .results_database import ResultsDatabase

"""
Provides a class used for compiling a database of the output from TDA codes.
"""


class ResultsToRabbitMQ:
    """
    Provides a class passing the results of various tasks to a RabbitMQ message queue.
    """

    def __init__(self, broker="amqp://guest:guest@rabbitmq-service:5672", queue="results"):
        """
        Open a handle to the message queue we send job results to.

        :param broker:
            The URL of the RabbitMQ broker we should send output to.
        :param queue:
            The name of the message queue we feed output into.
        """
        self.broker = broker
        self.queue = queue

        self.connection = pika.BlockingConnection(pika.URLParameters(url=self.broker))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue)

    def record_timing(self, tda_code, target_name, task_name, lc_length, result):
        """
        Create a new entry in the message queue for transit detection results.

        :param tda_code:
            The name of the Transit Detection Algorithm being used.
        :type tda_code:
            str
        :param target_name:
            The name of the target / lightcurve being analysed.
        :type target_name:
            str
        :param task_name:
            The name of the processing step being performed on the lightcurve.
        :type task_name:
            str
        :param lc_length:
            The length of the lightcurve (seconds)
        :type lc_length:
            float
        :param result:
            Data structure containing the output from the TDA code
        :return:
            None
        """

        json_message = json.dumps({
            'tda_code': tda_code,
            'target_name': target_name,
            'task_name': task_name,
            'lc_length': lc_length,
            'result': result
        })

        self.channel.basic_publish(exchange='', routing_key=self.queue, body=json_message)

    def close(self):
        """
        Close connection to the RabbitMQ message queue.

        :return:
            None
        """

        self.channel.close()


class ResultsToMySQL:
    """
    Provides a class passing the results of various tasks to a MySQL database.
    """

    def __init__(self, results_database=None):
        """
        Open a handle to the database we are to send results to.

        :param results_database:
            The class we use to communicate with the MySQL database
        """

        if results_database is None:
            results_database = ResultsDatabase()

        self.results_database = results_database

    def read_from_rabbitmq(self, broker="amqp://guest:guest@rabbitmq-service:5672", queue="results"):
        """
        Blocking call to read messages from RabbitMQ and send them to MySQL.

        :param broker:
            The URL of the RabbitMQ broker we should send output to.
        :param queue:
            The name of the message queue we feed output into.
        """
        broker = broker
        queue = queue

        connection = pika.BlockingConnection(pika.URLParameters(url=broker))
        channel = connection.channel()
        channel.queue_declare(queue=queue)

        def callback(ch, method, properties, body):
            logging.info("Received run time message <{}>".format(body))

            message = json.loads(body)

            self.record_timing(tda_code=message['tda_code'],
                               target_name=message['target_name'],
                               task_name=message['task_name'],
                               lc_length=message['lc_length'],
                               run_time_wall_clock=message['run_time_wall_clock'],
                               run_time_cpu=message['run_time_cpu']
                               )

        logging.info("Waiting for messages")
        channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)
        channel.start_consuming()

    def record_timing(self, tda_code, target_name, task_name, lc_length, result):
        """
        Create a new entry in the database for a transit detection result.

        :param tda_code:
            The name of the Transit Detection Algorithm being used.
        :type tda_code:
            str
        :param target_name:
            The name of the target / lightcurve being analysed.
        :type target_name:
            str
        :param task_name:
            The name of the processing step being performed on the lightcurve.
        :type task_name:
            str
        :param lc_length:
            The length of the lightcurve (seconds)
        :type lc_length:
            float
        :param result:
            Data structure containing the output from the TDA code
        :return:
            None
        """

        self.results_database.record_result(
            tda_code=tda_code,
            target_name=target_name,
            task_name=task_name,
            lc_length=lc_length,
            result_structure=result
        )
