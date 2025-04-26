from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from PIL import Image
import google.generativeai as genai
import base64
import io
import traceback
from functools import wraps
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a1b2c3d4e5f678901234567890abcdef0123456789abcdef012345')

genai.configure(api_key=os.environ.get('AIzaSyC90IKUxsCklSmoAVWstXfxm0tBT1YfRJo'))
model = genai.GenerativeModel('gemini-1.5-flash')

users = {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash('Login Successful!', 'success')
            return redirect(url_for('home'))
        else:
            return render_template('SignUp_LogIn_Form.html', error="Invalid credentials", active_form='login')
    return render_template('SignUp_LogIn_Form.html', error=None, active_form='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email')

        if username in users:
            return render_template('SignUp_LogIn_Form.html', error="Username already exists", active_form='register')

        hashed_password = generate_password_hash(password)
        users[username] = {'password': hashed_password, 'email': email}
        return redirect(url_for('login'))
    return render_template('SignUp_LogIn_Form.html', error=None, active_form='register')

@app.route('/')
@login_required
def home():
    return render_template("index.html")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/image', methods=['POST'])
@login_required
def analyze_uploaded_image():
    try:
        if 'image' not in request.files:
            return jsonify({'response': "❗ No image uploaded."}), 400

        file = request.files['image']

        # Image type and size check
        if file.mimetype not in ['image/jpeg', 'image/png']:
            return jsonify({'response': "❗ Only JPEG and PNG images are supported."}), 400

        if file.content_length and file.content_length > 5 * 1024 * 1024:
            return jsonify({'response': "❗ Image size exceeds 5MB."}), 400

        image = Image.open(file).convert("RGB")
        image_part = pil_to_gemini_part(image)

        prompt = (
            "You are a professional photo analysis assistant. "
            "Examine the uploaded photo and describe the following: "
            "1. The number and appearance of people, including facial expressions and attire. "
            "2. Any notable individuals or celebrities present, with brief identification and context if recognizable. "
            "3. Visible objects and background details. "
            "Conclude with practical suggestions to improve the photo’s quality, composition, or appeal."
        )

        response = model.generate_content([prompt, image_part])

        username = session.get('username', 'User')
        response_text = f"Hello {username}, here’s what I see in your photo:\n\n{response.text}"
        return jsonify({'response': response_text})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'response': f"Oops! Couldn't analyze the image. Error: {str(e)}"}), 500

@app.route('/analyze', methods=['POST'])
@login_required
def analyze_captured_image():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'response': "❗ No image data received."}), 400

        base64_data = data['image'].split(",")[1]
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        image_part = pil_to_gemini_part(image)

        prompt = (
            "You are a professional photo analysis assistant. "
            "Examine the uploaded photo and describe the following: "
            "1. Any notable individuals or celebrities present, with brief identification and context if recognizable. "
            "2. The number and appearance of people, including facial expressions and attire. "
            "3. Visible objects and background details. "
            "Conclude with practical suggestions to improve the photo’s quality, composition, or appeal."
        )

        response = model.generate_content([prompt, image_part])

        username = session.get('username', 'User')
        response_text = f"Hello {username}, here’s what I see in your photo:\n\n{response.text}"
        return jsonify({'response': response_text})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'response': f"Oops! Couldn't analyze the image. Error: {str(e)}"}), 500

def pil_to_gemini_part(pil_img):
    img_byte_arr = io.BytesIO()
    pil_img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return {
        "mime_type": "image/jpeg",
        "data": img_byte_arr.read()
    }

if __name__ == "__main__":
    app.run(debug=True)
