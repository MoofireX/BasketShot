import math
import cv2
import numpy as np

class basketshot():
    def __init__(self,img,height=float,weight=float,athleticism=int):
        self.height = height * 0.0254
        self.weight = weight * 0.453592
        self.img = img
        self.athleticism = athleticism
        self.cross_Section_Area = 0.045
        self.mass = 0.624
        self.gravity = 9.8 #m/s**2
        self.air_density = 1.225 #kgm/ft**3
        self.ball_weight = self.mass * self.gravity
        self.hoop_pos = (64.95, 240.35)
        self.Cd = 0.47
        img = cv2.imread(self.img)
        h, w, _ = img.shape
        rows = 10
        columns = 10
        tile_h = h // rows
        tile_w = w // rows
        self.sub_images = {}
        for r in range(rows):
            for c in range(columns):
                start_y = r * tile_h
                end_y = (r+1) * tile_h
                start_x = c * tile_w
                end_x = (c+1) * tile_w

                sub_image = img[start_y:end_y, start_x:end_x]
                self.sub_images[(r,c)] = sub_image
                cv2.imwrite(f'/home/suraj/Desktop/BasketShot/static/sub_image{r}{c}.png', sub_image)
    def air_resistance_formula(self,air_density,velocity,crosssection_area):
        drag = (1/2)*air_density*math.pow(velocity,2)*self.Cd*crosssection_area
        return drag
    def parabola_vars(self,theta,x1,x2,y1,y2):
        if (x2 - x1) == 0:
            return 0, 0, y1
        
        if (x1 - x2) == 0:
            return 0, 0, y1 
        a = math.tan(math.radians(theta)) / (x1-x2)
        b = ((y2 - y1) - a * (math.pow(x2,2) - math.pow(x1,2))) / (x2 - x1)
        c = y1 - (a*(math.pow(x1,2))) - b*x1
        
        return a, b, c
    def parabolic_shot(self,a,b,c,x):
        shot = a*(math.pow(x,2))+(b*x)+c
        if self.athleticism == 1:
            percent = 0.4
        elif self.athleticism == 2:
            percent = 0.5
        else:
            percent = 0.7
        push = percent * self.weight * self.gravity
        distance_to_hoop = abs(self.hoop_pos[0] - x)
        velocity = math.sqrt(distance_to_hoop * self.gravity)

        drag_force = self.air_resistance_formula(self.air_density, velocity, self.cross_Section_Area)
        net_force = push - drag_force
        if net_force < 0:
            net_force = 0.001
        acceleration = net_force / self.mass
        if acceleration <= 0:
            acceleration = 0.1  
        force = self.mass * acceleration
        release_time = math.sqrt(self.height/acceleration) + math.sqrt((2*((5/6)*self.height))/acceleration)
        return shot, acceleration, force, release_time
    def calculate_shots(self):
        for position,_ in self.sub_images.items():
            distance_x = self.hoop_pos[0] - position[0]
            distance_y = self.hoop_pos[1] - position[1]
            distance = math.sqrt(math.pow(distance_x, 2) + math.pow(distance_y, 2))
            a1, b1, c1 = self.parabola_vars(50,position[0], self.hoop_pos[0], self.height, self.hoop_pos[1])
            a2, b2, c2 = self.parabola_vars(40,position[0], self.hoop_pos[0], self.height, self.hoop_pos[1])
            shots_x = np.linspace(position[0], self.hoop_pos[0], 100)
            shots_y = (self.parabolic_shot(a1,b1,c1,distance_x),self.parabolic_shot(a2,b2,c2,distance_x))
        return shots_x, shots_y, self.sub_images, distance
