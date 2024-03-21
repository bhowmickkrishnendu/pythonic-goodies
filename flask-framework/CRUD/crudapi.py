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

@app.route('/deleteUser', methods=['DELETE'])
def delete_user():
    data = request.get_json()

    username = data.get('username')

    cursor = db.cursor()
    # Check if the username exists
    query = "SELECT * FROM user_login WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"message": "User not found"}), 404

    # Delete the user
    delete_query = "DELETE FROM user_login WHERE username = %s"
    cursor.execute(delete_query, (username,))
    db.commit()

    return jsonify({"message": "User deleted successfully"}), 200

@app.route('/viewProfile', methods=['GET'])
def view_profile():
    data = request.get_json()
    username = data.get('username')

    app.logger.info("Received request for username: %s", username)

    cursor = db.cursor()
    query = "SELECT firstname, lastname, email, phone_number FROM user_login WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    if user:
        firstname, lastname, email, phone_number = user
        profile_data = {
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "phone_number": phone_number
        }
        return jsonify(profile_data), 200
    else:
        return jsonify({"message": "User not found"}), 404
    
@app.route('/updateUser', methods=['PUT'])
def update_user():
    data = request.get_json()
    username = data.get('username')
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    email = data.get('email')
    phone_number = data.get('phone_number')

    # Validate input data (you can add more validation as needed)
    if not all([firstname, lastname, email, phone_number]):
        return jsonify({"message": "Missing required fields"}), 400

    # Check if the user exists
    cursor = db.cursor()
    query = "SELECT * FROM user_login WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"message": "User not found"}), 404

    # Update user data in the database
    update_query = "UPDATE user_login SET firstname = %s, lastname = %s, email = %s, phone_number = %s WHERE username = %s"
    cursor.execute(update_query, (firstname, lastname, email, phone_number, username))
    db.commit()

    return jsonify({"message": "User data updated successfully"}), 200


if __name__ == '__main__':
    app.run(debug=True)

