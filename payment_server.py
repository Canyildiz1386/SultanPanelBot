from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/verify', methods=['GET'])
def verify_payment():
    # Simply return "OK" without any verification logic
    return jsonify({"status": "OK", "message": "Payment received and processed."})

if __name__ == '__main__':
    app.run(port=5000)
