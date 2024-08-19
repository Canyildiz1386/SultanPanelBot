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

if __name__ == '__main__':
    app.run(debug=True)
