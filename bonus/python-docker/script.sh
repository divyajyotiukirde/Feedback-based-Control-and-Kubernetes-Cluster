#!/bin/sh

kubectl proxy &

python3 -m flask run --host=0.0.0.0