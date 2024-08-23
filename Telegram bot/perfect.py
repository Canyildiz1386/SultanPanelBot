import uuid

def build_payment_form(payee_account, payee_name, amount, currency, return_url, notify_url):
    # Unique payment ID
    payment_id = str(uuid.uuid4())

    # Perfect Money URL to submit the payment form to
    perfectmoney_url = 'https://perfectmoney.is/api/step1.asp'

    # Fields required by Perfect Money
    fields = {
        'PAYMENT_ID': payment_id,
        'PAYEE_ACCOUNT': payee_account,
        'PAYEE_NAME': payee_name,
        'PAYMENT_AMOUNT': amount,
        'PAYMENT_UNITS': currency,
        'STATUS_URL': notify_url,
        'PAYMENT_URL': return_url,
        'PAYMENT_URL_METHOD': 'POST',
        'NOPAYMENT_URL': return_url,
        'NOPAYMENT_URL_METHOD': 'POST',
        'BAGGAGE_FIELDS': 'INVOICES',
        'PAYMENT_METHOD': 'Pay Now!',
    }

    # Generate HTML form
    form_html = f'<form action="{perfectmoney_url}" method="POST">\n'
    for key, value in fields.items():
        form_html += f'    <input type="hidden" name="{key}" value="{value}"/>\n'
    form_html += '    <input type="submit" value="Pay Now"/>\n'
    form_html += '</form>'

    return form_html


# Example usage
payee_account = 'U38406992'  # Your Perfect Money account ID
payee_name = 'YourBusiness'  # Your business name
amount = '10.00'  # Amount to be paid
currency = 'USD'  # Currency
return_url = 'https://yourwebsite.com/payment-success'  # URL for successful payment
notify_url = 'https://yourwebsite.com/payment-notification'  # URL for payment notification

payment_form_html = build_payment_form(payee_account, payee_name, amount, currency, return_url, notify_url)

# Output the form HTML
print(payment_form_html)
