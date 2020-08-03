from functools import wraps
import flask
from flask import Flask, jsonify, request,send_file
from flask.wrappers import Response
from flask_jwt_extended import JWTManager, jwt_required, create_access_token,get_jwt_identity,get_jwt_claims,verify_jwt_in_request
from flask_cors import CORS,cross_origin
import datetime
from datetime import date,timedelta,datetime
from collections import OrderedDict 
from flask_jwt_extended.utils import current_user
import mysql.connector
import json
from cryptoauth import walletcheckout,walletbalance,profiledetails,wallettranfer,addmoneyadmin,deductmoneyadmin
import pandas as pd
import bcrypt
import uuid 




app = Flask(__name__)
CORS(app)
# Setup the Flask-JWT-Extended extension
app.config['JSON_SORT_KEYS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this!
jwt = JWTManager(app)

@jwt.user_claims_loader
def add_claims_to_access_token(identity):
    if identity in ['admin']:
        return {'role': 'admin'}
    else:
        return {'role': 'user'}

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt_claims()
        print(claims)
        if claims['role'] != 'admin':
            return jsonify(msg='Admins only!'), 403
        else:
            return fn(*args, **kwargs)
    return wrapper

@jwt.expired_token_loader
def my_expired_token_callback():
    return jsonify({'msg': 'The Token has expired'}), 401


@app.route('/login', methods=['POST','OPTIONS'])
@cross_origin()
def login():
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    mycursor = connection.cursor()
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request","status":"error"}), 400
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    password = password.encode('utf-8')
    expires = timedelta(hours=1)
    if not username:
        return jsonify({"msg": "Missing username parameter","status":"error"}), 400
    if not password:
        return jsonify({"msg": "Missing password parameter","status":"error"}), 400

    mycursor.execute("SELECT * FROM users WHERE username='%s' AND status='None'"% username)
    myresult = mycursor.fetchone()
    try:
        hashed = myresult[3].encode('utf-8')
        if bcrypt.checkpw(password, hashed):
            # Identity can be any data that is json serializable
            access_token = create_access_token(username,expires_delta=expires)
            return jsonify(access_token=access_token,status='sucess'), 200
        else:
            return jsonify({"msg": "Bad username or password","status":"error"}), 400
    except:
        return jsonify({"msg": "Bad username or password","status":"error"}), 400



@app.route('/protected')
@jwt_required
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

@app.route('/userproducts')
def userproducts():
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    mycursor = connection.cursor()
    if request.method=='GET':
        mycursor.execute("SELECT * FROM products ORDER by product_name")
        row_heading=[x[0] for x in mycursor.description]
        #for extracting tittle from db columns
        myresult = mycursor.fetchall()
        json_data=[]
        for x in myresult:
            json_data.append(dict(zip(row_heading,x)))
        return jsonify(json_data), 200
    
@app.route('/products',methods=['GET','POST','PUT','DELETE'])
@jwt_required
@admin_required
def products():
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    current_user = get_jwt_identity()
    mycursor = connection.cursor()
    if request.method=='GET':
        claims = get_jwt_claims()
        print(claims)
        mycursor.execute("SELECT * FROM products ORDER by product_name")
        row_heading=[x[0] for x in mycursor.description]
        #for extracting tittle from db columns
        myresult = mycursor.fetchall()
        json_data=[]
        for x in myresult:
            json_data.append(dict(zip(row_heading,x)))
        return jsonify(json_data), 200
    elif request.method=='POST':
        claims = get_jwt_claims()
        try:
            print('success')
            name = request.json.get('name', None)
            quantity = request.json.get('quantity', None)
            price = request.json.get('price', None)
            image = request.json.get('image', None)
            category = request.json.get('category', None)
            query = """INSERT INTO products (product_name, price, available, category,img) 
                                    VALUES 
                                    ('%s','%s','%s','%s','%s')""" % (name,price,quantity,category,image)
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            print('success')
            return 'success',200
        except:
            print('errro')
            return 'error',401
    elif request.method=='PUT':
        try:
            updateid = request.json.get('id', None)
            quantity = request.json.get('quantity', None)
            price = request.json.get('price', None)
            status = request.json.get('status',None)
            query = """UPDATE products SET price='%s', available='%s',status='%s'
                            WHERE id='%s'""" % (price,quantity,status,updateid)
            print('ksie')
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            print('success')
            return 'success',200
        except:
            return 'error',401
    
    elif request.method=='DELETE':
        try:
            updateid = request.json.get('id', None)

            query = """DELETE from products WHERE id='%s'""" % (updateid)
            print('ksie')
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            print('success')
            return 'success',200
        except:
            return 'error',401

@app.route('/checkout',methods=['POST'])
@cross_origin()
@jwt_required
def checkout():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request","status":"error"}), 400
    current_user = get_jwt_identity()
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    data=json.dumps(request.json)
    data=json.loads(data)
    month=datetime.now()
    month=month.strftime("%b-%Y")
    for n in range(len(data)):
        vals=data[n]
        total= int(vals['quantity'])*int(vals['price'])
        walletupdate=walletcheckout(current_user,total)
        if walletupdate=='success':
            trans_num = (uuid.uuid4()).hex 
            query = """INSERT INTO orders (transac_num,username, product, quantity, amount,category,month,status) 
                                VALUES 
                                ('%s','%s','%s','%s','%s','%s','%s','Billed')""" % (trans_num,current_user,vals['name'],vals['quantity'],total,vals['category'],month)

            cursor = connection.cursor()
            cursor.execute(query)
            mycursor = connection.cursor()
            mycursor.execute("SELECT * FROM products WHERE id='%s'" % (str(vals['id'])) )
            myresult = mycursor.fetchone()
            available=int(myresult[3])-int(vals['quantity'])
            if available>=0:
                update = """UPDATE products SET available = '%s' WHERE id = '%s'""" % (available,vals['id'])
                cursor = connection.cursor()
                cursor.execute(update)
                connection.commit()
                return jsonify('data'), 200
            else:
                return jsonify({'msg':'required quantity not available'}), 401
        else:
            return jsonify({'msg':'insufficientfunds'}), 401


@app.route('/profile',methods=['GET'])
@cross_origin()
@jwt_required
def profile():
    current_user = get_jwt_identity()
    print(current_user)
    profiledata=profiledetails(current_user)
    print(profiledata)
    return jsonify(profiledata),200

@app.route('/wallet',methods=['GET','POST'])
@cross_origin()
@jwt_required
def wallet():
    current_user = get_jwt_identity()
    if request.method=='GET':
        balance=walletbalance(current_user)
        return jsonify({'wallet':balance}),200
    elif request.method=='POST':
        data=json.dumps(request.json)
        data=json.loads(data)
        targetemail=data['targetemail']
        amount=data['amount']
        msg=wallettranfer(current_user,targetemail,amount)
        if msg=='success':
           return 'success',200
        else:
           return 'error',401
    else:    
        return 'Only GET and POST methods allowed',401


@app.route('/userorders',methods=['GET'])
@cross_origin()
@jwt_required
def userorders():
    current_user = get_jwt_identity()
    print(current_user)
    connection = mysql.connector.connect(host='localhost',
                                        database='unpluged',
                                        user='root',
                                        password='')
    mycursor = connection.cursor()
    mycursor.execute("SELECT * FROM orders WHERE username='%s' ORDER BY id DESC" % current_user)
    row_heading=[x[0] for x in mycursor.description]
    #for extracting tittle from db columns
    myresult = mycursor.fetchall()
    json_data=[]
    for x in myresult:
        json_data.append(dict(zip(row_heading,x)))
    return jsonify(json_data),200

@app.route('/users',methods=['GET','POST','PUT','DELETE'])
@cross_origin()
@jwt_required
@admin_required
def users():
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    mycursor = connection.cursor()
    if request.method=='GET':
        user=request.args.get('user', '')
        print(user)
        try:
           data=profiledetails(user)
           return jsonify(data),200
        except:
            return 'error',401
    elif request.method=='POST':
        if not request.is_json:
            return jsonify({"msg": "Missing JSON in request","status":"error"}), 400
        username = request.json.get('username', None)
        name = request.json.get('name', None)
        email= request.json.get('email', None)
        password = request.json.get('password', None)
        department = request.json.get('department', None)
        phone = request.json.get('phone', None)
        passw=password.encode('utf-8')
        hashedpass= bcrypt.hashpw(passw, bcrypt.gensalt(rounds=14))
        
        query = """INSERT INTO users (username,name, password, email,phone,department) 
                                VALUES 
                                ('%s','%s','%s','%s','%s','%s')""" % (username,name,hashedpass.decode('utf-8'),email,phone,department)

        mycursor.execute(query)
        connection.commit()
        return 'sucess',200
    #for updating user details
    elif request.method=='PUT':
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        status = request.json.get('status', None)
        email = request.json.get('email', None)
        print(username)
        print(email)
        if len(password)==0:
            try:
                mycursor.execute("UPDATE users SET email='%s',status='%s' WHERE username='%s'" % (email,status,username))
                connection.commit()
                return jsonify({'msg':'update successful'}),200
            except:
                return 'error',401
        else:
            passw=password.encode('utf-8')
            hashedpass= bcrypt.hashpw(passw, bcrypt.gensalt(rounds=14))
            try:
                mycursor.execute("UPDATE users SET password='%s', email='%s',status='%s' WHERE username='%s'" % (hashedpass.decode('utf-8'),email,status,username))
                connection.commit()
                return jsonify({'msg':'update successful'}),200
            except:
                return 'error',401
    
    if request.method=='DELETE':
        username = request.json.get('username', None)
        try:
            mycursor.execute("DELETE FROM users WHERE username='%s'" % username)
            connection.commit()
            return jsonify({'msg':'delete successful'}),200
        except:
            return 'error',401

@app.route('/walletoptions',methods=['PUT','DELETE'])
@cross_origin()
@jwt_required
@admin_required
def addmoney():
    admin = get_jwt_identity()
    if request.method=='PUT':
        username = request.json.get('username', None)
        amount = request.json.get('amount', None)
        data=addmoneyadmin(username,admin,amount,'Credit')
        if data=='success':
            return jsonify({'msg':'success'}),200
        else:
            return jsonify({'msg':'username is incorrect'}),401
    elif request.method=='DELETE':
        username = request.json.get('username', None)
        amount = request.json.get('amount', None)
        data=deductmoneyadmin(username,admin,amount)
        if data=='success':
            return jsonify({'msg':'success'}),200
        else:
            return jsonify({'msg':'username is incorrect/not enough amount'}),401

@app.route('/orders',methods=['GET','DELETE','PUT'])
@cross_origin()
@jwt_required
@admin_required
def orders():
    admin = get_jwt_identity()
    connection = mysql.connector.connect(host='localhost',
                                            database='unpluged',
                                            user='root',
                                            password='')
    mycursor = connection.cursor()
    if request.method=='GET':
        orderdate=request.args.get('date', '')
        print(orderdate)
        mycursor.execute("SELECT * FROM orders where date='%s'" % orderdate)
        row_heading=[x[0] for x in mycursor.description]
        #for extracting tittle from db columns
        myresult = mycursor.fetchall()
        json_data=[]
        for x in myresult:
            json_data.append(dict(zip(row_heading,x)))
        return jsonify(json_data),200
    elif request.method=='DELETE':
        transac_num = request.json.get('transac_num', None)
        mycursor.execute("DELETE FROM orders where transac_num='%s'" % transac_num)
        connection.commit()
        return 'success',200
    elif request.method=='PUT':
        transac_num = request.json.get('transac_num', None)
        mycursor.execute("SELECT * FROM orders where transac_num='%s'" % transac_num)
        money = mycursor.fetchone()
        username=money[2]
        print(money[5])
        print(username)
        data=addmoneyadmin(username,admin,money[5],'Refund')
        if data=='success':
            mycursor.execute("UPDATE orders SET status='Refund' where transac_num='%s'" % transac_num)
            connection.commit()
            return jsonify({'msg':'success'}),200
        else:
            return jsonify({'msg':'no detail of order/invalid transac num'}),401

@app.route('/sales',methods=['GET','DELETE','PUT'])
@cross_origin()
@jwt_required
@admin_required
def sales():
    connection = mysql.connector.connect(host='localhost',
                                            database='unpluged',
                                            user='root',
                                            password='')
    mycursor = connection.cursor()
    if request.method=='GET':
        getdate=request.args.get('date', '')
        print(getdate)
        mycursor.execute("SELECT SUM(amount),SUM(quantity) FROM orders where date='%s'" % str(getdate))
        #for extracting tittle from db columns
        myresult = mycursor.fetchone()
        #print(myresult)
        mycursor.execute("SELECT SUM(amount) FROM transactions where date='%s' AND type='Credit'" % str(getdate))
        myresult1 = mycursor.fetchone()
        amount=myresult[0]
        quantity=myresult[1]
        addedamount=myresult1[0]
        return jsonify({'amount':amount,'orders':quantity,'addedamount':addedamount}),200

@app.route('/weeksales',methods=['GET','DELETE','PUT'])
@cross_origin()
@jwt_required
@admin_required
def weeksales():
    connection = mysql.connector.connect(host='localhost',
                                            database='unpluged',
                                            user='root',
                                            password='')
    mycursor = connection.cursor()
    if request.method=='GET':
        sdate = datetime.strptime(request.args.get('date', ''), "%Y-%m-%d")  # start date  datetime.strptime(request.args.get('date', ''), "%Y%m%d ")
        sdate=sdate.date()
        edate = sdate-timedelta(days=7)   # end date
        print(edate)
        delta = edate - sdate       # as timedelta
        print(delta)
        arr={}
        for i in range(0,delta.days + 1,-1):
            date = sdate + timedelta(days=i)
            mycursor.execute("SELECT SUM(amount) FROM orders where date='%s'" % str(date))
            myresult = mycursor.fetchone()
            arr[date.strftime("%A")]=myresult
        arr = OrderedDict(reversed(list(arr.items()))) 
        return jsonify(arr),200

@app.route('/monthsales',methods=['GET','DELETE','PUT'])
@cross_origin()
@jwt_required
@admin_required
def monthsales():
    connection = mysql.connector.connect(host='localhost',
                                            database='unpluged',
                                            user='root',
                                            password='')
    mycursor = connection.cursor()
    if request.method=='GET':
        sdate = datetime.strptime(request.args.get('date', ''), "%Y-%m-%d")  # start date  datetime.strptime(request.args.get('date', ''), "%Y%m%d ")
        month=sdate.date()
        arr={}
        for i in range(11):
            print(month)
            dbmonth=month.strftime("%b-%Y")
            mycursor.execute("SELECT SUM(amount) FROM orders where month='%s'" % dbmonth)
            myresult = mycursor.fetchone()
            arr[month.strftime("%b")]=myresult
            month=month.replace(day=1)
            month=month-timedelta(days=1)
        arr = OrderedDict(reversed(list(arr.items()))) 
        return jsonify(arr),200

@app.route('/transactions',methods=['GET','DELETE','PUT'])
@cross_origin()
@jwt_required
@admin_required
def transactions():
    connection = mysql.connector.connect(host='localhost',
                                            database='unpluged',
                                            user='root',
                                            password='')
    mycursor = connection.cursor()
    date=request.args.get('date', '')
    mycursor.execute("SELECT * FROM transactions where date='%s'" % date)
    myresult = mycursor.fetchall()
    row_heading=[x[0] for x in mycursor.description]
    json_data=[]
    for x in myresult:
        json_data.append(dict(zip(row_heading,x)))
    return jsonify(json_data),200


@app.route('/report',methods=['GET'])
@cross_origin()
#@jwt_required
#@admin_required
def report():
    #admin = get_jwt_identity()
    #print(admin)
    #connection = mysql.connector.connect(host='localhost',
     #                                       database='unpluged',
      #                                      user='root',
       #                                     password='')
    #mycursor = connection.cursor()
    #mycursor.execute("SELECT * FROM orders")
    #data = mycursor.fetchall()
    #columns = [desc[0] for desc in mycursor.description]
    #df = pd.DataFrame(list(data), columns=columns)'''
    #'''writer = pd.ExcelWriter('foo.xlsx')
    #df.to_excel(writer, sheet_name='bar')
    #writer.save()
    #return send_file('/home/kise/foo.xlsx',as_attachment=True),200'''
    return 'helllo', 200

@app.route('/billprint',methods=['GET','DELETE','PUT','POST'])
@cross_origin()
def billprint():
    connection = mysql.connector.connect(host='localhost',
                                            database='unpluged',
                                            user='root',
                                            password='')
    mycursor = connection.cursor()
    deviceid=request.args.get('deviceid', '')
    if deviceid=='123456':
        ordernumber=request.args.get('ordernumber', '')
        mycursor.execute("SELECT * FROM orders where transac_num='%s' AND status='Billed'" % ordernumber)
        result=mycursor.fetchone()
        if result:
            wallet = "UPDATE orders SET status = '%s' WHERE transac_num = '%s'" % ('Printed',ordernumber)
            mycursor.execute(wallet)
            connection.commit()
            return jsonify({'msg':'success','transac_num':result[1],'product':result[3],'quantity':result[4],'amount':result[5],'date':result[7]}),200
        else:
            return jsonify({'msg':'already printed'}),403
    else:
        return jsonify({'msg':'Unauthorized access'}),401


if __name__ == '__main__':
    app.run(debug=True)
