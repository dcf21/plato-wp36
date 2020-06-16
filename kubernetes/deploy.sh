#!/bin/bash

mkdir -p ../datadir/mysql
chmod 775 ../datadir/mysql

kubectl apply -f mysql-pv.yaml
kubectl apply -f mysql-deployment.yaml

kubectl apply -f rabbitmq-service.yaml
kubectl apply -f rabbitmq-controller.yaml

kubectl apply -f datadir-pv.yaml
kubectl apply -f lightcurves-pv.yaml
kubectl apply -f plato-deployment.yaml
