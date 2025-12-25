import cv2
import numpy as np
import pytesseract
import re
from collections import deque
from PIL import Image

class TrafficViolationDetector:
    def __init__(self, cascade_path, num_frames_avg=10):
        # Tải Haar Cascade từ đường dẫn trong config
        self.license_plate_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Khởi tạo hàng đợi để làm mượt đường kẻ (từ class LineDetector)
        self.y_start_queue = deque(maxlen=num_frames_avg)
        self.y_end_queue = deque(maxlen=num_frames_avg)
        
        # Danh sách biển số vi phạm trong phiên làm việc hiện tại
        self.penalized_texts = []

    def detect_traffic_light_color(self, image, rect):
        """Trích nguyên văn từ cell detect_traffic_light_color"""
        x, y, w, h = rect
        roi = image[y:y+h, x:x+w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        red_lower = np.array([0, 120, 70])
        red_upper = np.array([10, 255, 255])
        yellow_lower = np.array([20, 100, 100])
        yellow_upper = np.array([30, 255, 255])

        red_mask = cv2.inRange(hsv, red_lower, red_upper)
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        font = cv2.FONT_HERSHEY_TRIPLEX
        font_scale = 1  
        font_thickness = 2  
        
        if cv2.countNonZero(red_mask) > 0:
            text_color = (0, 0, 255)
            message = "Detected Signal Status: Stop"
            color = 'red'
        elif cv2.countNonZero(yellow_mask) > 0:
            text_color = (0, 255, 255)
            message = "Detected Signal Status: Caution"
            color = 'yellow'
        else:
            text_color = (0, 255, 0)
            message = "Detected Signal Status: Go"
            color = 'green'
            
        cv2.putText(image, message, (15, 70), font, font_scale+0.5, text_color, font_thickness+1, cv2.LINE_AA)
        cv2.putText(image, 34*'-', (10, 115), font, font_scale, (255,255,255), font_thickness, cv2.LINE_AA)
        
        return image, color

    def detect_white_line(self, frame, color, 
                          slope1=0.03, intercept1=920, slope2=0.03, intercept2=770, slope3=-0.8, intercept3=2420):
        """Trích nguyên văn từ class LineDetector"""
        
        def get_color_code(color_name):
            color_codes = {'red': (0, 0, 255), 'green': (0, 255, 0), 'yellow': (0, 255, 255)}
            return color_codes.get(color_name.lower())

        frame_org = frame.copy()
        
        def line1(x): return slope1 * x + intercept1
        def line2(x): return slope2 * x + intercept2
        def line3(x): return slope3 * x + intercept3

        height, width, _ = frame.shape
        
        # Logic tạo mask bằng vòng lặp for (nguyên bản từ cell)
        mask3 = frame.copy()
        for x in range(width):
            mask3[int(line1(x)):, x] = 0
        for x in range(width):
            mask3[:int(line2(x)), x] = 0
        for y in range(height):
            mask3[y, :int(line3(y))] = 0

        gray = cv2.cvtColor(mask3, cv2.COLOR_BGR2GRAY)
        blurred_gray = cv2.GaussianBlur(gray, (7, 7), 0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray_clahe = clahe.apply(blurred_gray)

        edges = cv2.Canny(gray, 30, 100)
        dilated_edges = cv2.dilate(edges, None, iterations=1)
        edges = cv2.erode(dilated_edges, None, iterations=1)

        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=160, maxLineGap=5)

        x_start, x_end = 0, width - 1
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                slope = (y2 - y1) / (x2 - x1 + np.finfo(float).eps)
                intercept = y1 - slope * x1
                self.y_start_queue.append(int(slope * x_start + intercept))
                self.y_end_queue.append(int(slope * x_end + intercept))

        avg_y_start = int(sum(self.y_start_queue) / len(self.y_start_queue)) if self.y_start_queue else 0
        avg_y_end = int(sum(self.y_end_queue) / len(self.y_end_queue)) if self.y_end_queue else 0

        line_start_ratio = 0.32
        x_start_adj = x_start + int(line_start_ratio * (x_end - x_start))
        avg_y_start_adj = avg_y_start + int(line_start_ratio * (avg_y_end - avg_y_start))

        mask = np.zeros_like(frame)
        cv2.line(mask, (x_start_adj, avg_y_start_adj), (x_end, avg_y_end), (255, 255, 255), 4)

        color_code = get_color_code(color)
        channel_indices = [1] if color_code == (0, 255, 0) else [2] if color_code == (0, 0, 255) else [1, 2] if color_code == (0, 255, 255) else []
        
        for idx in channel_indices:
            frame[mask[:,:,idx] == 255, idx] = 255
                
        slope_avg = (avg_y_end - avg_y_start) / (x_end - x_start + np.finfo(float).eps)
        intercept_avg = avg_y_start - slope_avg * x_start

        mask_line = np.copy(frame_org)
        for x in range(width):
            y_line = slope_avg * x + intercept_avg - 35
            mask_line[:int(y_line), x] = 0 

        return frame, mask_line

    def extract_license_plate(self, frame, mask_line):
        """Trích nguyên văn từ cell extract_license_plate"""
        gray = cv2.cvtColor(mask_line, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        kernel = np.ones((2, 2), np.uint8)
        gray = cv2.erode(gray, kernel, iterations=1)

        non_black_points = cv2.findNonZero(gray)
        if non_black_points is None: return frame, []
        
        x, y, w, h = cv2.boundingRect(non_black_points)
        w = int(w * 0.7)
        cropped_gray = gray[y:y+h, x:x+w]

        license_plates = self.license_plate_cascade.detectMultiScale(cropped_gray, scaleFactor=1.07, minNeighbors=15, minSize=(20, 20))
        license_plate_images = []

        for (x_plate, y_plate, w_plate, h_plate) in license_plates:
            cv2.rectangle(frame, (x_plate + x, y_plate + y), (x_plate + x + w_plate, y_plate + y + h_plate), (0, 255, 0), 3)
            license_plate_image = cropped_gray[y_plate:y_plate+h_plate, x_plate:x_plate+w_plate]
            license_plate_images.append(license_plate_image)

        return frame, license_plate_images

    def apply_ocr(self, license_plate_image):
        _, img = cv2.threshold(license_plate_image, 120, 255, cv2.THRESH_BINARY)

        pil_img = Image.fromarray(img)

        full_text = pytesseract.image_to_string(pil_img, config='--psm 6')
        text = full_text.strip()

        
        if "BW" in text:
            text = text.replace("BW", "NN")
        elif "8W" in text: 
            text = text.replace("8W", "NN")
            
        return text

    def draw_penalized_list(self, frame):
        """Trích nguyên văn từ cell draw_penalized_text"""
        font = cv2.FONT_HERSHEY_TRIPLEX
        font_scale = 1  
        font_thickness = 2
        color = (255, 255, 255)
        y_pos = 180
        
        cv2.putText(frame, 'Fined license plates:', (25, y_pos), font, font_scale, color, font_thickness)
        y_pos += 80

        for text in self.penalized_texts:
            cv2.putText(frame, '->  '+text, (40, y_pos), font, font_scale, color, font_thickness)
            y_pos += 60

    def process_video(self, video_path):
        """Hàm điều phối (dựa trên logic hàm main() trong cell)"""
        vid = cv2.VideoCapture(video_path)
        self.penalized_texts = [] # Reset cho mỗi lần chạy video
        
        while True:
            ret, frame = vid.read()
            if not ret:
                break

            rect = (1700, 40, 100, 250) 
            frame, color = self.detect_traffic_light_color(frame, rect)
            frame, mask_line = self.detect_white_line(frame, color)
            
            if color == 'red':
                frame, license_plate_images = self.extract_license_plate(frame, mask_line)
                for lp_img in license_plate_images:
                    text = self.apply_ocr(lp_img)
                    
                    # Pattern lọc từ cell main()
                    if text is not None and re.match("^[A-Z]{2}\s[0-9]{3,4}$", text) and text not in self.penalized_texts:
                        self.penalized_texts.append(text)
                        print(f"Fined license plate: {text}")

            if self.penalized_texts:
                self.draw_penalized_list(frame)
        
        vid.release()
        return self.penalized_texts