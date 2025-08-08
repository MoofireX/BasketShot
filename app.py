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
            github_url = "https://raw.githubusercontent.com/yourusername/yourrepo/main/court.jpg"
            urllib.request.urlretrieve(github_url, court_image_path)
        except Exception as e:
            print(f"Error downloading court image: {e}")
            # Create a placeholder if download fails
            placeholder_img = np.ones((600, 800, 3), dtype=np.uint8) * 128
            cv2.imwrite(court_image_path, placeholder_img)
    return court_image_path

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            height = float(request.form['height'])
            weight = float(request.form['weight'])
            athleticism = int(request.form['athleticism'])

            # Use the embedded court image
            image_path = ensure_court_image()

            # Clear old tiles
            for f in os.listdir(app.config['TILES_FOLDER']):
                if f.startswith('tile_'):
                    os.remove(os.path.join(app.config['TILES_FOLDER'], f))

            # Generate shots
            b = basketshot(img=image_path, height=height, weight=weight, athleticism=athleticism)
            shots_x, shots_y, sub_images, distance = b.calculate_shots()

            tiles = []
            hoop_height_m = 3.048 # Standard 10ft hoop height in meters

            for (r, c), img in sub_images.items():
                img_filename = f'tile_{r}_{c}.png'
                img_path = os.path.join(app.config['TILES_FOLDER'], img_filename)
                cv2.imwrite(img_path, img)

                # Calculate physics for this specific position
                distance_x = b.hoop_pos[0] - r
                
                # We'll calculate for two different parabolas (different launch angles)
                a1, b1, c1 = b.parabola_vars(45, r, b.hoop_pos[0], b.height, hoop_height_m)
                a2, b2, c2 = b.parabola_vars(55, r, b.hoop_pos[0], b.height, hoop_height_m)

                # The original parabolic_shot seems to be for a single point, let's get the other metrics from it
                shot, acceleration, force, release_time = b.parabolic_shot(a1, b1, c1, distance_x)

                tiles.append({
                    'r': r,
                    'c': c,
                    'filename': img_filename,
                    'acceleration': f'{acceleration:.2f}',
                    'force': f'{force:.2f}',
                    'release_time': f'{release_time:.2f}',
                    'parabolas': [
                        {'a': a1, 'b': b1, 'c': c1, 'angle': 45},
                        {'a': a2, 'b': b2, 'c': c2, 'angle': 55}
                    ],
                    'x_start': r,
                    'x_end': b.hoop_pos[0]
                })

            return render_template('index.html', tiles=tiles)
            
        except Exception as e:
            print(f"Error processing request: {e}")
            return render_template('index.html', tiles=[], error=str(e))

    return render_template('index.html', tiles=[])

if __name__ == '__main__':
    app.run(debug=True)
