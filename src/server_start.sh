#! /bin/bash

export FLASK_APP="server_api.py"
export FLASK_DEBUG=1
export YOURAPPLICATION_SETTINGS=PATH_TO_CFG_FILE
source PATH_TO_SOURCEME_FOR_JAVA_PROCESSES

python -m flask run --host=0.0.0.0 --port=5050 --with-threads
