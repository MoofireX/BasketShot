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
            github_url = "https://raw.githubusercontent.com/MoofireX/basketshot-frontend/main/nbacourt.jpg"
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

                # We'll calculate for two different parabolas (different launch angles)
                launch_angle_1 = 45
                launch_angle_2 = 55
                a1, b1, c1 = b.parabola_vars(launch_angle_1, r, b.hoop_pos[0], b.height, hoop_height_m)
                a2, b2, c2 = b.parabola_vars(launch_angle_2, r, b.hoop_pos[0], b.height, hoop_height_m)

                # --- Corrected physics calculations ---
                y = hoop_height_m - b.height
                g = b.gravity
                
                theta_rad_1 = math.radians(launch_angle_1)
                cos_theta_sq_1 = math.cos(theta_rad_1)**2
                tan_theta_1 = math.tan(theta_rad_1)
                denominator_1 = 2 * cos_theta_sq_1 * (distance_x * tan_theta_1 - y)
                
                acceleration, force, release_time = 0, 0, 0

                if denominator_1 > 0:
                    v0_squared = (g * distance_x**2) / denominator_1
                    if v0_squared > 0:
                        v0 = math.sqrt(v0_squared)
                        push_distance = b.height / 3 
                        
                        if b.athleticism == 1: athleticism_factor = 1.2
                        elif b.athleticism == 2: athleticism_factor = 1.0
                        else: athleticism_factor = 0.8

                        force = ((0.5 * b.mass * v0_squared) / push_distance) * athleticism_factor
                        drag_force = b.air_resistance_formula(b.air_density, v0, b.cross_Section_Area)
                        net_force = force - drag_force
                        if net_force <= 0: net_force = 0.001

                        acceleration = net_force / b.mass
                        if acceleration <= 0: acceleration = 0.1

                        release_time = math.sqrt(2 * push_distance / acceleration)

                tiles.append({
                    'r': r,
                    'c': c,
                    'filename': img_filename,
                    'acceleration': f'{acceleration:.2f}',
                    'force': f'{force:.2f}',
                    'release_time': f'{release_time:.2f}',
                    'parabolas': [
                        {'a': a1, 'b': b1, 'c': c1, 'angle': launch_angle_1},
                        {'a': a2, 'b': b2, 'c': c2, 'angle': launch_angle_2}
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
