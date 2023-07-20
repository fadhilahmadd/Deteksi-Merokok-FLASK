from flask import Flask, request, jsonify, render_template, redirect, url_for, session, Response, json, request, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Resource, Api, reqparse
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt, os,random
from flask_mail import Mail, Message
import functools, base64, operator

import subprocess


# YOLOv8
from datetime import datetime
import mysql.connector
from ultralytics import YOLO
from YOLO_Video import deteksi_realtime

app = Flask(__name__)
api = Api(app)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:@127.0.0.1:3306/deteksimerokok"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = 'whateveryouwant'
# mail env config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
mail = Mail(app)
# mail env config
db = SQLAlchemy(app)

class Users(db.Model):
    id       = db.Column(db.Integer(), primary_key=True, nullable=False)
    nama     = db.Column(db.String(30), nullable=False)
    email    = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_verified = db.Column(db.Boolean(),nullable=False)
    createdAt = db.Column(db.Date)
    updatedAt = db.Column(db.Date)

#parserRegister
regParser = reqparse.RequestParser()
regParser.add_argument('nama', type=str, help='nama', location='json', required=True)
regParser.add_argument('email', type=str, help='Email', location='json', required=True)
regParser.add_argument('password', type=str, help='Password', location='json', required=True)
regParser.add_argument('confirm_password', type=str, help='Confirm Password', location='json', required=True)


@api.route('/register')
class Registration(Resource):
    @api.expect(regParser)
    def post(self):
        # BEGIN: Get request parameters.
        args        = regParser.parse_args()
        nama        = args['nama']
        email       = args['email']
        password    = args['password']
        password2   = args['confirm_password']
        is_verified = False

        # cek confirm password
        if password != password2:
            return {
                'messege': 'Password tidak cocok'
            }, 400

        #cek email sudah terdaftar
        user = db.session.execute(db.select(Users).filter_by(email=email)).first()
        if user:
            return "Email sudah terpakai silahkan coba lagi menggunakan email lain"
        user          = Users()
        user.nama     = nama
        user.email    = email
        user.password = generate_password_hash(password)
        user.is_verified = is_verified
        db.session.add(user)
        msg = Message(subject='Verification OTP',sender=os.environ.get("MAIL_USERNAME"),recipients=[user.email])
        token =  random.randrange(10000,99999)
        session['email'] = user.email
        session['token'] = str(token)
        msg.html=render_template(
        'verify_email.html', token=token)
        mail.send(msg)
        db.session.commit()
        return {'message':
            'Registrasi Berhasil. Silahkan cek email untuk verifikasi.'}, 201

otpparser = reqparse.RequestParser()
otpparser.add_argument('otp', type=str, help='otp', location='json', required=True)
@api.route('/verify')
class Verify(Resource):
    @api.expect(otpparser)
    def post(self):
        args = otpparser.parse_args()
        otp = args['otp']
        if 'token' in session:
            sesion = session['token']
            if otp == sesion:
                email = session['email']

                user = Users.query.filter_by(email=email).first()
                user.is_verified = True
                db.session.commit()
                session.pop('token',None)
                return {'message' : 'Email berhasil diverifikasi'}
            else:
                return {'message' : 'Kode Otp Salah'}
        else:
            return {'message' : 'Kode Otp Salah'}
logParser = reqparse.RequestParser()
logParser.add_argument('email', type=str, help='Email', location='json', required=True)
logParser.add_argument('password', type=str, help='Password', location='json', required=True)

@api.route('/login')
class LogIn(Resource):
    @api.expect(logParser)
    def post(self):
        args        = logParser.parse_args()
        email       = args['email']
        password    = args['password']
        # cek jika kolom email dan password tidak terisi
        if not email or not password:
            return {
                'message': 'Email Dan Password Harus Diisi'
            }, 400
        #cek email sudah ada
        user = db.session.execute(
            db.select(Users).filter_by(email=email)).first()
        if not user:
            return {
                'message': 'Email / Password Salah'
            }, 400
        else:
            user = user[0]
        #cek password
        if check_password_hash(user.password, password):
            if user.is_verified == True:
                token= jwt.encode({
                        "user_id":user.id,
                        "user_email":user.email,
                        "exp": datetime.utcnow() + timedelta(hours= 1)
                },app.config['SECRET_KEY'],algorithm="HS256")

                tup = email,":",password
                #toString
                data = functools.reduce(operator.add, tup)
                byte_msg = data.encode('ascii')
                base64_val = base64.b64encode(byte_msg)
                code = base64_val.decode('ascii')
                msg = Message(subject='Verification OTP',sender=os.environ.get("MAIL_USERNAME"),recipients=[user.email])
                msg.html=render_template('verify_email.html', token=token)
                mail.send(msg)

                return {'message' : 'Login Berhasil',
                        'token' : token,
                        'code' : code
                        },200
            else:
                return {'message' : 'Email Belum Diverifikasi ,Silahka verifikasikan terlebih dahulu '},401
        else:
            return {
                'message': 'Email / Password Salah'
            }, 400

def decodetoken(jwtToken):
    decode_result = jwt.decode(
               jwtToken,
               app.config['SECRET_KEY'],
               algorithms = ['HS256'],
            )
    return decode_result

authParser = reqparse.RequestParser()
authParser.add_argument('Authorization', type=str, help='Authorization', location='headers', required=True)
@api.route('/user')
class DetailUser(Resource):
       @api.expect(authParser)
       def get(self):
        args = authParser.parse_args()
        bearerAuth  = args['Authorization']
        try:
            jwtToken    = bearerAuth[7:]
            token = decodetoken(jwtToken)
            user =  db.session.execute(db.select(Users).filter_by(email=token['user_email'])).first()
            user = user[0]
            data = {
                'nama' : user.nama,
                'email' : user.email
            }
        except:
            return {
                'message' : 'Token Tidak valid,Silahkan Login Terlebih Dahulu!'
            }, 401

        return data, 200

editParser = reqparse.RequestParser()
editParser.add_argument('nama', type=str, help='nama', location='json', required=True)
editParser.add_argument('Authorization', type=str, help='Authorization', location='headers', required=True)
@api.route('/edituser')
class EditUser(Resource):
       @api.expect(editParser)
       def put(self):
        args = editParser.parse_args()
        bearerAuth  = args['Authorization']
        nama = args['nama']
        datenow =  datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        try:
            jwtToken    = bearerAuth[7:]
            token = decodetoken(jwtToken)
            user = Users.query.filter_by(email=token.get('user_email')).first()
            user.nama = nama
            user.updatedAt = datenow
            db.session.commit()
        except:
            return {
                'message' : 'Token Tidak valid,Silahkan Login Terlebih Dahulu!'
            }, 401
        return {'message' : 'Update User Sukses'}, 200


verifyParser = reqparse.RequestParser()
verifyParser.add_argument(
    'otp', type=str, help='OTP', location='json', required=True)


@api.route('/verify')
class Verify(Resource):
    @api.expect(verifyParser)
    def post(self):
        args = verifyParser.parse_args()
        otp = args['otp']
        try:
            user = Users.verify_token(otp)
            if user is None:
                return {'message' : 'Verifikasi gagal'}, 401
            user.is_verified = True
            db.session.commit()
            return {'message' : 'Akun sudah terverifikasi'}, 200
        except Exception as e:
            print(e)
            return {'message' : 'Terjadi error'}, 200
#editpasswordParser
editPasswordParser =  reqparse.RequestParser()
editPasswordParser.add_argument('current_password', type=str, help='current_password',location='json', required=True)
editPasswordParser.add_argument('new_password', type=str, help='new_password',location='json', required=True)
@api.route('/editpassword')
class Password(Resource):
    @api.expect(authParser,editPasswordParser)
    def put(self):
        args = editPasswordParser.parse_args()
        argss = authParser.parse_args()
        bearerAuth  = argss['Authorization']
        cu_password = args['current_password']
        newpassword = args['new_password']
        try:
            jwtToken    = bearerAuth[7:]
            token = decodetoken(jwtToken)
            user = Users.query.filter_by(id=token.get('user_id')).first()
            if check_password_hash(user.password, cu_password):
                user.password = generate_password_hash(newpassword)
                db.session.commit()
            else:
                return {'message' : 'Password Lama Salah'},400
        except:
            return {
                'message' : 'Token Tidak valid! Silahkan, Sign in!'
            }, 401
        return {'message' : 'Password Berhasil Diubah'}, 200

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    return render_template('dashboard.html')


@app.route("/deteksi", methods=['GET','POST'])

def deteksi():
    session.clear()
    return render_template('deteksi.html')

# To display the Output Video on Webcam page
@app.route('/realtime')
def realtime():
    #return Response(generate_frames(path_x = session.get('video_path', None),conf_=round(float(session.get('conf_', None))/100,2)),mimetype='multipart/x-mixed-replace; boundary=frame')
    return Response(deteksi_realtime(),mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/visualisasi')
def visualisasi():
    # Run Streamlit script using subprocess
    subprocess.run(['streamlit', 'run', 'streamlit_app.py', '--server.enableCORS=False'])
    return render_template('visualisasi.html')

cnx = mysql.connector.connect(
    host="localhost",  
    user="root",  
    password="",  
    database="deteksimerokok"  
)
#create object to execute sql query
cursor = cnx.cursor
insert_query = "INSERT INTO data (kondisi) VALUES (%s)"

@app.route("/data", methods=['GET'])
def ambil_data():
    cursor = cnx.cursor()
    cursor.execute("SELECT kondisi, COUNT(*) AS value FROM data GROUP BY kondisi")

    data = cursor.fetchall()
    result = []
    for row in data:
        result.append({
            'kondisi' : row[0],
            'value' : row[1]
        })
    cursor.close()
    return jsonify(result)

if __name__ == '__main__':
    # DEBUG is SET to TRUE. CHANGE FOR PROD
    # app.run(debug=True)
    app.run(host='192.168.193.223', port=5000, debug=True)