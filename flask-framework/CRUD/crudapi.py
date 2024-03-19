from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="krish",
    password="Krish@1209",
    database="basic_app"
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

if __name__ == '__main__':
    app.run(debug=True)

