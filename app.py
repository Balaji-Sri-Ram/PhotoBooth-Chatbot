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

import time

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a1b2c3d4e5f678901234567890abcdef0123456789abcdef012345')

genai.configure(api_key=os.environ.get('GOOGLE_API_KEY', 'AIzaSyDxiPCvWmCWxKBGPe8gkPZyUfoxhb8aKB0'))
model = genai.GenerativeModel('gemini-2.0-flash')

users = {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

import re

def generate_with_retry(model, content, retries=5, initial_delay=5):
    """Generates content with retry logic for rate limits."""
    delay = initial_delay
    for attempt in range(retries):
        try:
            return model.generate_content(content)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota exceeded" in error_msg:
                # Try to parse the specific retry delay from the error message
                # Pattern looks like: retry_delay {\n  seconds: 33\n}
                retry_match = re.search(r'retry_delay\s*{\s*seconds:\s*(\d+)', error_msg)
                
                if retry_match:
                    wait_time = int(retry_match.group(1)) + 2 # Add a small buffer
                    print(f"Quota exceeded, waiting {wait_time}s as requested by API...")
                    time.sleep(wait_time)
                    # Don't increase delay exponentially if we have a specific wait time
                    continue 
                
                if attempt < retries - 1:
                    print(f"Quota exceeded, retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
            raise e
    return None # Should not reach here due to raise

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
            "You are a professional photo analysis assistant."
            "Examine the uploaded photo and provide the following analysis:"
            "1. Count and describe all visible people, including facial expressions, clothing, and notable physical features."
            "2. If any celebrity or well-known individual is detected, identify them and provide a brief background — including their profession, notable achievements, and why they might be recognizable."
            "3. Describe other visible objects, surroundings, and the background setting in detail."
            "Finally, suggest practical ways to improve the overall quality, composition, or appeal of the photo."
        )

        response = generate_with_retry(model, [prompt, image_part])

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
            "You are a professional photo analysis assistant."
            "Examine the uploaded photo and provide the following analysis:"
            "1. Count and describe all visible people, including facial expressions, clothing, and notable physical features."
            "2. If any celebrity or well-known individual is detected, identify them and provide a brief background — including their profession, notable achievements, and why they might be recognizable."
            "3. Describe other visible objects, surroundings, and the background setting in detail."
            "Finally, suggest practical ways to improve the overall quality, composition, or appeal of the photo."
        )

        response = generate_with_retry(model, [prompt, image_part])

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
