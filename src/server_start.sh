#! /bin/bash

export FLASK_APP="server_api.py"
export FLASK_DEBUG=1
python -m flask run --host=0.0.0.0 --port=5050 --with-threads
