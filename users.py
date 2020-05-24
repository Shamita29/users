from flask import Flask,request, jsonify,render_template,abort, session,Response
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import datetime 
import os
import re
import requests
import hashlib 
from sqlalchemy.sql import select,exists
from sqlalchemy.orm import load_only
import csv
import sys, time
from sqlalchemy.orm import backref

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'rideshare.db')
db = SQLAlchemy(app)
ma = Marshmallow(app)



class User(db.Model):

    __tablename__ = "user"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(128))
    #fkey = db.relationship('Ride', back_populates='parent')
    posts = db.relationship('UserRide', backref='user', lazy='dynamic')
    ride = db.relationship('Ride', cascade='all,delete',secondary= 'user_ride', backref='user')

    def __init__(self, username, password):
    	self.username = username
    	self.password = password

    def serialize(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'password':self.password}


class Ride(db.Model):

    __tablename__ = "ride"

    ride_id = db.Column(db.Integer,autoincrement=True,primary_key=True)
    created= db.Column(db.String(50), nullable=False)
    src_adr= db.Column(db.String(50), nullable=False)
    dest_adr = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.String(50))
    #user_id = db.Column(db.Integer, db.ForeignKey('user.user'), nullable=False)
    #parent = db.relationship('User')


    #rides = db.relationship('User', backref='ride', passive_deletes=True)
    def serialize(self):
        #return "<Ride ride_id=%s created=%s source_adr=%s dest_adr=%s timestamp=%s>" % (self.ride_id, self.created,
        return {
        'ride_id':self.ride_id,
        'created':self.created,
        'src_adr':self.src_adr,
        'dest_adr':self.dest_adr,
        'timestamp':self.timestamp,
        }

class UserRide(db.Model):

    __tablename__ = "user_ride"

    user_ride_id = db.Column(db.Integer,
                          autoincrement=True,
                          primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey("ride.ride_id"), nullable=False)
    ride = db.relationship('Ride', uselist=False) 


    def __repr__(self):
        s = "<UserRide user_ride_id=%s user_id=%s ride_id=%s >"
        return s % (self.user_ride_id, self.user_id, self.ride_id)

class joinRide(db.Model):
    __tablename__ = "userdetails"

   
    user_ride_id = db.Column(db.Integer,
                          autoincrement=True,
                          primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey("ride.ride_id"), nullable=False)
    ride = db.relationship('Ride', uselist=False)  

    def serialize(self):
        return {
        'user_ride_id':self.user_ride_id,
        'username':self.username,
        'ride_id':self.ride_id
        
        }

class DataDisplay(ma.Schema):
    class Meta:
        fields = ('username','password','user_id','ride_id','created','src_adr','dest_adr','timestamp')


data_display = DataDisplay()
datas_display = DataDisplay(many=True)

def formatTheDate(s):    
    line=s.split(" ")
    yymmdd=line[0].split('-')
    hhms=line[1].split(':')
    yy=yymmdd[0]
    mm=yymmdd[1]
    dd=yymmdd[2]
    hh=hhms[0]
    m=hhms[1]
    s=str(int(float(hhms[2])))
    return(dd+'-'+mm+'-'+yy+':'+s+'-'+m+'-'+hh)
    

def is_in_format(s):
    if(re.match(r'[0-3]{2}-[0-9]{2}-[0-9]{4}:[0-5][0-9]-[0-5][0-9]-[0-5][0-9]',s) is None):
        return 1
    else:
        return 0

def checkingArea(num):
    file=open("AreaNameEnum.csv","r")
    line={}
    i=0;
    for lines in file:
        if i==0:
            i+=1
        else:
            l=lines.split(',')
            line[int(l[0])]=int(l[0])
    file.close()
    return (num in line)

def isupcoming(data1,data2):
    line1=data1.split(':')
    line2=data2.split(':')
    date1=line1[0]
    time1=line1[1]
    date2=line2[0]
    time2=line2[1]
    result=comparewithdate(date1,date2)
    if(result==1):
        return True
    elif result==0:
        return comparewithtime(time1,time2)
    else:
        return False

def comparewithtime(time1,time2):
    arg1=time1.split('-')
    arg2=time2.split('-')
    l=list(zip(arg1,arg2))
    l.reverse()
    for(j,i) in l:
        i=int(i)
        j=int(j)
        if(i>j):
            return True
        elif i<j:
            return False
def comparewithdate(date1,date2):
    ddmmyy1=date1.split('-')
    ddmmyy2=date2.split('-')
    result=-1
    l=list(zip(ddmmyy1,ddmmyy2))
    l.reverse()
    for(j,i) in l:
        i=int(i)
        j=int(j)
        if(i>j):
            result=1
            break
        elif i==j:
            result=0
        else:
            result=-1
            break
    return result


@app.route("/api/v1/users", methods=["PUT"])
def add_user():
    if (request.method=="PUT"):
        _username = request.json['username']
        _password = request.json['password']
        result = hashlib.sha1(_password.encode()) 
        pwd=result.hexdigest()
        if(re.match(r'[0-9a-fA-F]{40}$',_password) is None):
            return jsonify({"flag":"password mismatch"}),400
        else:

        	readquery={
        	"table":"user",
        	"column":"user",
        	"where":"username",
            "data":_username
        	}
        	
                read=requests.post(url='http://0.0.0.0:80/api/v1/db/read',json=readquery)   
        	if read==200:
        		return jsonify({}),400
        	else:
        		sqlquery={"table":"user","query":"insert","username":_username, "password":pwd}
        		#que={"usern":_username,"password":pwd}s
        		res=requests.post(url='http://0.0.0.0:80/api/v1/db/write',json=sqlquery)
        		if res==200:
        			return jsonify({}),201
        		else:
        			return Response(status=400)
    else:
        return Response(status=405)



@app.route("/api/v1/users/<username>", methods=["DELETE"])
def user_delete(username):
    #print(username)
    readquery={"table":"user","column":"user","where":"username", "data":username}
    read=requests.post(url='http://0.0.0.0:80/api/v1/db/read',json=readquery)
    if read==200:
        sqlquery={"table":"user","query":"delete","usern":username}
        res=requests.post(url='http://0.0.0.0:80/api/v1/db/write',json=sqlquery)
        if res==200:
            return jsonify({}),200
        else:
            return Response(status=204)
    else:
        return Response(status=204)
    


#db.create_all()
@app.route("/api/v1/users",methods=["GET"])
def list_users():
    try:                
        readquery={"table":"userlist","query":"listuser"}
        res=requests.post(url='http://0.0.0.0:80/api/v1/db/read',json=readquery)
        if res==200:
           return jsonify(res),200
    except:
        return {},400

if __name__ == "__main__":
    app.debug = True
    app.run()
