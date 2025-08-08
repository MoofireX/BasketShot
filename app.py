from flask import Flask, render_template, request, redirect, url_for
from flask_cors import CORS
import os
import cv2
import numpy as np
from basketshot import basketshot
import math
import urllib.request

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['TILES_FOLDER'] = 'static/tiles'
CORS(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TILES_FOLDER'], exist_ok=True)

# Download and save the court image if it doesn't exist
def ensure_court_image():
    court_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'court.jpg')
    if not os.path.exists(court_image_path):
        try:
            # Replace with your GitHub raw URL
            github_url = "https://raw.githubusercontent.com/MoofireX/BasketShot/main/static/nbacourt.jpg"
            urllib.request.urlretrieve(github_url, court_image_path)
        except Exception as e:
            print(f"Error downloading court image: {e}")
    return court_image_path

@app.route('/', methods=['GET', 'POST'])
def index():
    court_image_path = ensure_court_image()
    court_image_url = None
    if os.path.exists(court_image_path):
        court_image_url = os.path.join(os.path.basename(app.config['UPLOAD_FOLDER']), os.path.basename(court_image_path)).replace('\\', '/')

    if request.method == 'POST':
        try:
            height = float(request.form['height'])
            weight = float(request.form['weight'])
            athleticism = int(request.form['athleticism'])

            # Use the embedded court image
            image_path = court_image_path

            # Clear old tiles
            for f in os.listdir(app.config['TILES_FOLDER']):
                if f.startswith('tile_'):
                    os.remove(os.path.join(app.config['TILES_FOLDER'], f))

            # Generate shots
            b = basketshot(img=image_path, height=height, weight=weight, athleticism=athleticism)
            
            tiles = []
            hoop_height_m = 3.048 # Standard 10ft hoop height in meters

            for (r, c), img in b.sub_images.items():
                img_filename = f'tile_{r}_{c}.png'
                img_path = os.path.join(app.config['TILES_FOLDER'], img_filename)
                cv2.imwrite(img_path, img)

                # Calculate physics for this specific position
                distance_x = b.hoop_pos[0] - r
                if distance_x <= 0: continue

                # --- Unified Physics Calculations ---
                def calculate_shot_physics(launch_angle, start_r):
                    # 1. Define constants and initial conditions
                    y_diff = hoop_height_m - b.height
                    g = b.gravity
                    theta_rad = math.radians(launch_angle)
                    cos_theta = math.cos(theta_rad)
                    tan_theta = math.tan(theta_rad)

                    if cos_theta == 0: return 0, 0, 0, 0, 0, 0
                    cos_theta_sq = cos_theta**2

                    # 2. Calculate Initial Velocity (v0) needed to make the shot
                    # Based on the projectile motion equation: y = x*tan(theta) - (g*x^2)/(2*v0^2*cos^2(theta))
                    v0_squared_denominator = 2 * cos_theta_sq * (distance_x * tan_theta - y_diff)
                    if v0_squared_denominator <= 0: return 0, 0, 0, 0, 0, 0
                    v0_squared = (g * distance_x**2) / v0_squared_denominator

                    # 3. Calculate Parabola Coefficients (a, b, c) from v0
                    # This ensures the plotted path matches the physics
                    a = -g / (2 * v0_squared * cos_theta_sq)
                    b_val = tan_theta - (2 * a * start_r)
                    c_val = b.height - (start_r * tan_theta) + (a * start_r**2)

                    # 4. Calculate Shot Dynamics (Force, Acceleration, Time)
                    push_distance = b.height / 3
                    if b.athleticism == 1: athleticism_factor = 0.8
                    elif b.athleticism == 2: athleticism_factor = 1.0
                    else: athleticism_factor = 1.2

                    # Work-Energy Theorem: Force = (0.5 * mass * v0^2) / distance
                    force = (0.5 * b.mass * v0_squared) / push_distance
                    # Newton's Second Law: a = F/m, adjusted for skill
                    acceleration = (force / b.mass) * athleticism_factor
                    
                    release_time = 0
                    if acceleration > 0:
                        # Kinematics: t = sqrt(2*d/a)
                        release_time = math.sqrt(2 * push_distance / acceleration)

                    return a, b_val, c_val, acceleration, force, release_time

                # We'll calculate for two different parabolas (different launch angles)
                launch_angle_1 = 45
                launch_angle_2 = 55
                
                a1, b1, c1, acc1, force1, time1 = calculate_shot_physics(launch_angle_1, r)
                a2, b2, c2, acc2, force2, time2 = calculate_shot_physics(launch_angle_2, r)

                tiles.append({
                    'r': r,
                    'c': c,
                    'filename': img_filename,
                    'parabolas': [
                        {'a': a1, 'b': b1, 'c': c1, 'angle': launch_angle_1, 'acceleration': f'{acc1:.2f}', 'force': f'{force1:.2f}', 'release_time': f'{time1:.2f}'},
                        {'a': a2, 'b': b2, 'c': c2, 'angle': launch_angle_2, 'acceleration': f'{acc2:.2f}', 'force': f'{force2:.2f}', 'release_time': f'{time2:.2f}'}
                    ],
                    'x_start': r,
                    'x_end': b.hoop_pos[0]
                })

            return render_template('index.html', tiles=tiles, court_image_url=court_image_url)
            
        except Exception as e:
            print(f"Error processing request: {e}")
            return render_template('index.html', tiles=[], error=str(e), court_image_url=court_image_url)

    return render_template('index.html', tiles=[], court_image_url=court_image_url)

if __name__ == '__main__':
    app.run(debug=True)
