from flask import Flask, jsonify, request
import thread
import sys
import subprocess
import json
import os
import re
import hashlib
import urllib
from pymongo import MongoClient
from smtplib import SMTPDataError

from flask_mail import Mail, Message
from raven.contrib.flask import Sentry

from lxml import html
import urllib2

from flask import redirect
from flask import url_for
from werkzeug.utils import secure_filename

import time
import datetime

def create_app():
    app = Flask(__name__)

    app.config.from_object(__name__)
    
    # Load default config and override config from cfg file
    app.config.from_envvar('YOURAPPLICATION_SETTINGS')
   
    return app

app=create_app()

def processFile(userId, deviceId, filepath):
    print "./fairwind-unzip raffaele.montella@gmail Pippo "+str(userId)+" "+str(deviceId)+" "+str(filepath)
    print "Unzipping..."

    params=[]
    if app.config['SCHEDULER'] is not None:
        params.append(app.config['SCHEDULER'])
    params.extend((app.config['UNZIPPER_PATH'], app.config['PRK_PATH'], app.config['SRC_PBK_PATH'],str(userId),str(deviceId),str(filepath)))

    p = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      
    out, err = p.communicate()
    result=json.loads(out)
    print "...done! Result: "+str(result)

    if "success" in result['status']:
        print "Success!"
        if len(result['data'])>0:
            client = MongoClient(app.config['DATABASE_NAME'])
            db = client[app.config['DATABASE_NAME']]
            signalk = db['signalk']
            print "Adding to mongodb..."
            for data in result['data']:
                ts = time.time()
                timeStamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%SZ')
                print "Adding:"+str(timeStamp)+" - "+str(data['context'])
                signalk.insert_one({ "userid":userId,"deviceid":deviceId,"data":data,"timestamp":timeStamp})
            print "...done!"
        else:
            print "No data to import"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['json']

@app.route('/generatekeys', methods=['POST'])
def generatekeys():
	result={"status":"fail","public_key":"unknown"}
	if request.method == 'POST':
		# check if the post request has source public key
		sourcePublicKey = None
		try:
			sourcePublicKey=request.form.get('sourcePublicKey')
			# save source public key
			file = open(app.config['SRC_PBK_PATH'], 'w') 
			file.write(sourcePublicKey)
			file.close()
		except:
			e = sys.exc_info()[0]
			print e
		# generate destination public and private key if not exist
		publicKey = None
		if not os.path.isfile(app.config['PBK_PATH']) or not os.path.isfile(app.config['PRK_PATH']):
			p = subprocess.Popen([app.config['KEYSGENERATOR_PATH'],app.config['PRK_PATH'],app.config['PBK_PATH']])
			p.wait()
		file = open(app.config['PBK_PATH'], 'r') 
		publicKey = file.read() 
		file.close()
		if publicKey is not None:
			result={"status":"success","publicKey":publicKey}
	return jsonify(result)

@app.route('/upload', methods=['POST'])
def upload():
    result={"status":"fail","message":"unknown" }

    print "upload"
    if request.method == 'POST':
        # check if the post request has the sessionid part
        sessionId=None
        try:
            sessionId=request.args.get('sessionid')
        except:
            e = sys.exc_info()[0]
            print e
        print "sessionId:"+str(sessionId)
        if sessionId is None:
            result={"status":"fail","message":"No sessionId","sessionid":None}
        else:
            # check if the post request has the deviceid part
            deviceId=None
            try:
                deviceId=request.args.get('deviceid')
            except:
                e = sys.exc_info()[0]
                print e
            print "deviceId:"+str(deviceId)
            if deviceId is None:
                result={"status":"fail","message":"No deviceId","sessionid":sessionId}
            else:
                # check if the post request has the sessionid part
                userId=None
                try:
                    #userId=request.form['userid']
                    userId=request.args.get('userid')
                except:
                    e = sys.exc_info()[0]
                    print e
                print "userId:"+str(userId)
                if userId is None:
                    result={"status":"fail","message":"No userId","sessionid":sessionId}
                else:
                    # check if the post request has the file part
                    if 'file' not in request.files:
                        result={"status":"fail","message":"No file part","sessionid":sessionId}
                    else:
                        file = request.files['file']
                        print "file:"+str(file.filename)

                        # if user does not select file, browser also
                        # submit a empty part without filename
                        if file.filename == '':
                            result={"status":"fail","message":"No selected file","sessionid":sessionId}
                        else:
                            if file and allowed_file(file.filename):
                                filename = secure_filename(file.filename)
                                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                                print "filepath:"+filepath
                                file.save(filepath)
                                thread.start_new_thread(processFile, (userId, deviceId, filepath))

                                result={"status":"success","message":"Ok","sessionid":str(sessionId)}
                            else:
                                result={"status":"fail","message":"Not allowed file","sessionid":str(sessionId)}
        print "Result:"
        print str(result)
        print "----------------------------"
        return jsonify(result)
        
