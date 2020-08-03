import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import mysql.connector
import uuid 

password = b"kisekise"
salt = b'1234567890123456'
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
    backend=default_backend()
)
key = base64.urlsafe_b64encode(kdf.derive(password))
f = Fernet(key)
#token = f.encrypt(b"23")

def walletcheckout(username,price):
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    
    #print(token)
    #print(f.decrypt(token))
    try:
        mycursor = connection.cursor()
        mycursor.execute("SELECT * FROM users WHERE username='%s'" % (username) )
        myresult = mycursor.fetchone()
        kisedata=myresult[4].encode('utf-8')
        myresult=f.decrypt(kisedata)
        remaining=int(myresult)-int(price)
        if remaining>=0:
            remaining=f.encrypt(str(remaining).encode('utf-8')) 
            wallet = "UPDATE users SET amount = '%s' WHERE id = '%s'" % (remaining.decode('utf-8'),'1')
            cursor = connection.cursor()
            cursor.execute(wallet)
            connection.commit()
            print('sucesss')
            return 'success'
        else:
            print('eroro')
            return 'error'
    except:
        return 'error'

def walletbalance(username):
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')

    mycursor = connection.cursor()
    mycursor.execute("SELECT * FROM users WHERE username='%s'" % (username) )
    myresult = mycursor.fetchone()
    try:
        kisedata=myresult[4].encode('utf-8')
        mybalance=f.decrypt(kisedata)
        return mybalance
    except:
        return 0

def profiledetails(username):
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')

    mycursor = connection.cursor()
    mycursor.execute("SELECT * FROM users WHERE username='%s'" % (username) )
    my = mycursor.fetchone()
    mybalance=walletbalance(username)
    profiledata={'username':my[1],'name':my[2],'pass':my[3],'email':my[5],'phone':my[6],'group':my[7],'wallet':mybalance,'status':my[8]}
    return profiledata

def wallettranfer(username,targetemail,amount):
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    
    mycursor = connection.cursor()
    #for getting sender balance
    mycursor.execute("SELECT * FROM users WHERE username='%s'" % (username) )
    myresult = mycursor.fetchone()
    kisedata=myresult[4].encode('utf-8')
    myresult=f.decrypt(kisedata)
    remaining=int(myresult)-int(amount)
    if remaining>=0:
        #for reducing sender balance
        remaining=f.encrypt(str(remaining).encode('utf-8')) 
        wallet = "UPDATE users SET amount = '%s' WHERE username = '%s'" % (remaining.decode('utf-8'),username)
        cursor = connection.cursor()
        cursor.execute(wallet)
        #get current balance of receiver
        mycursor.execute("SELECT * FROM users WHERE username='%s'" % (targetemail) )
        myresult = mycursor.fetchone()
        targetdata=myresult[4].encode('utf-8')
        tarresult=f.decrypt(targetdata)
        updated=int(tarresult)+int(amount)
        updated=f.encrypt(str(updated).encode('utf-8'))
        #updating the receiver balance
        wallet = "UPDATE users SET amount = '%s' WHERE username = '%s'" % (updated.decode('utf-8'),targetemail)
        cursor = connection.cursor()
        cursor.execute(wallet)
        connection.commit()
        print('sucesss')
        return 'success'
    else:
        print('eroro')
        return 'error'

def addmoneyadmin(username,admin,amount,ordtype):
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    cursor = connection.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username='%s'" % (username) )
    myresult = cursor.fetchone()
    trans_num = (uuid.uuid4()).hex 
    if myresult:
        try:
            targetdata=myresult[4].encode('utf-8')
            tarresult=f.decrypt(targetdata)
            print(tarresult)
            updated=int(tarresult)+int(amount)
            updated=f.encrypt(str(updated).encode('utf-8'))
            #updating the receiver balance 
            wallet = "UPDATE users SET amount = '%s' WHERE username = '%s'" % (updated.decode('utf-8'),username)
            trans="""INSERT INTO transactions (transac_num,user,admin, amount,type) 
                                    VALUES 
                                    ('%s','%s','%s','%s','%s')""" % (trans_num,username,admin,amount,ordtype)
        except:
            updated=f.encrypt(str(amount).encode('utf-8'))
            #updating the receiver balance
            wallet = "UPDATE users SET amount = '%s' WHERE username = '%s'" % (updated.decode('utf-8'),username)
            trans="""INSERT INTO transactions (transac_num,user,admin, amount,type) 
                                    VALUES 
                                    ('%s','%s','%s','%s','Credit')""" % (trans_num,username,admin,amount)
        cursor.execute(wallet)
        cursor.execute(trans)
        connection.commit()
        print('sucesss')
        return 'success'
    else:
        return 'error'

def deductmoneyadmin(username,admin,amount):
    connection = mysql.connector.connect(host='localhost',
                                          database='unpluged',
                                          user='root',
                                          password='')
    mycursor = connection.cursor()
    trans_num = (uuid.uuid4()).hex 
    mycursor.execute("SELECT * FROM users WHERE username='%s'" % (username) )
    myresult = mycursor.fetchone()
    if myresult:
        try:
            targetdata=myresult[4].encode('utf-8')
            tarresult=f.decrypt(targetdata)
            updated=int(tarresult)-int(amount)
            updated=f.encrypt(str(updated).encode('utf-8'))
            #updating the receiver balance
            wallet = "UPDATE users SET amount = '%s' WHERE username = '%s'" % (updated.decode('utf-8'),username)
            trans="""INSERT INTO transactions (transac_num,user,admin, amount,type) 
                                        VALUES 
                                        ('%s','%s','%s','%s','Debit')""" % (trans_num,username,admin,amount)
            cursor = connection.cursor()
            cursor.execute(wallet)
            cursor.execute(trans)
            connection.commit()
            print('sucesss')
            return 'success'
        except:
            return 'error'
    else:
        return 'error'