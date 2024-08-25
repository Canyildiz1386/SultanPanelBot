from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os

app = Flask(__name__)

# Set default language
default_language = 'en'

# Route to serve images from the images folder
@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(os.path.join(app.root_path, 'images'), filename)

# Route to switch languages
@app.route('/switch_language')
def switch_language():
    global default_language
    lang = request.args.get('lang', 'en')
    default_language = lang
    return redirect(url_for('index'))

# Main route to serve the homepage
@app.route('/')
def index():
    lang = default_language
    return render_template('index.html', lang=lang)

# Route to handle Perfect Money payment confirmation
@app.route('/payment-confirmed', methods=['GET', 'POST'])
def payment_confirmed():
    # Extract payment details from the request
    payment_id = request.args.get('PAYMENT_ID')
    payment_amount = request.args.get('PAYMENT_AMOUNT')
    payer_account = request.args.get('PAYER_ACCOUNT')

    # Here you would verify the payment details and update your database
    # For now, we'll just print the details
    print(f"Payment confirmed. ID: {payment_id}, Amount: {payment_amount}, Payer: {payer_account}")

    # Redirect the user to a confirmation page or thank you page
    return "Payment confirmed! Thank you for your purchase."

# Route to handle failed payments for Perfect Money
@app.route('/payment-failed', methods=['GET', 'POST'])
def payment_failed():
    # You can extract details here if necessary
    payment_id = request.args.get('PAYMENT_ID')
    print(f"Payment failed for Payment ID: {payment_id}")

    # Redirect to a failure page or notify the user
    return "Payment failed. Please try again."

# Route to handle payment status updates (both for Perfect Money and Payeer)
@app.route('/payment-status', methods=['POST'])
def payment_status():
    # Extract payment status details from the request
    # Perfect Money posts this data in a specific format; you should verify the details here
    payment_id = request.form.get('PAYMENT_ID') or request.form.get('m_orderid')
    status = request.form.get('PAYMENT_STATUS') or request.form.get('status')
    payment_amount = request.form.get('PAYMENT_AMOUNT') or request.form.get('m_amount')

    # Implement your logic to update the order status in your database
    if status == 'Completed':
        print(f"Payment completed for Payment ID: {payment_id}, Amount: {payment_amount}")
        # Update order status to completed in the database
    elif status == 'Failed':
        print(f"Payment failed for Payment ID: {payment_id}")
        # Update order status to failed in the database

    return "Payment status updated."

# Additional routes for Payeer (if necessary, similar to Perfect Money)
@app.route('/payeer-confirmed', methods=['GET', 'POST'])
def payeer_confirmed():
    payment_id = request.args.get('m_orderid')
    payment_amount = request.args.get('m_amount')
    currency = request.args.get('m_curr')

    # Handle payment confirmation, verify, and update database
    print(f"Payeer payment confirmed. ID: {payment_id}, Amount: {payment_amount} {currency}")

    return "Payeer payment confirmed! Thank you for your purchase."

@app.route('/payeer-failed', methods=['GET', 'POST'])
def payeer_failed():
    payment_id = request.args.get('m_orderid')
    print(f"Payeer payment failed for Payment ID: {payment_id}")

    return "Payeer payment failed. Please try again."

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=80)
