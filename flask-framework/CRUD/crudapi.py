from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="krish",
    password="Krish@1209",
    database="main_app"
)


@app.route('/', methods=['GET'])
def index():
    return "<h1>Hello World!</h1>"

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    username=data.get('username')
    password=data.get('password')

    cursor = db.cursor()

    query = "SELECT user_id, firstname, lastname FROM user_login WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()

    if user:
        user_id, firstname, lastname = user
        return jsonify({"message": f"Thank you {firstname} {lastname}" }), 200
    else:
        return jsonify({"message": "Invalid username or password"}), 401

@app.route('/signUp', methods=['POST'])
def signup():
    data = request.get_json()

    firstname = data.get('firstname')
    lastname = data.get('lastname')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    phone_number = data.get('phone_number')

    if password != confirm_password:
        return jsonify({"message": "Password and confirm password do not match."}), 400
    
    if len(str(phone_number)) != 10:
        return jsonify({"message": "Phone number should be 10 digits"}), 400
    
    cursor = db.cursor()
    query = "SELECT * FROM user_login WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    if user:
        return jsonify({"message": "Username already taken"}), 400
    
    insert_query = "INSERT INTO user_login (firstname, lastname, email, username, password, phone_number) VALUES (%s, %s, %s, %s, %s, %s)"
    cursor.execute(insert_query, (firstname, lastname, email, username, password, phone_number))
    db.commit()

    return jsonify({"message": "User created successfully"}), 201



if __name__ == '__main__':
    app.run(debug=True)
