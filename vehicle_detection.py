import cv2
import numpy as np
import requests
from io import BytesIO
import threading
import time

# ตั้งค่า ESP32-CAM IP (เปลี่ยนเป็น IP ที่ได้จาก Serial Monitor)
ESP32_CAM_URL = "http://192.168.137.80/stream"  # อัปเดตตาม IP ใหม่
# ลดภาระประมวลผลเพื่อลดอาการค้างเมื่อมีวัตถุจำนวนมาก
PROCESS_EVERY_N = 3  # ตรวจจับทุก ๆ N เฟรม
BLOB_INPUT_SIZE = (320, 320)  # ลดขนาดอินพุตของ YOLO

# โหลด YOLO model
def load_yolo():
    print("Loading YOLO model...")
    net = cv2.dnn.readNet("yolov4.weights", "yolov4.cfg")
    
    # โหลด class names
    with open("coco.names", "r") as f:
        classes = [line.strip() for line in f.readlines()]
    
    # ได้ output layer names - วิธีที่ปลอดภัยกว่า
    layer_names = net.getLayerNames()
    unconnected = net.getUnconnectedOutLayers()
    
    # ตรวจสอบประเภทของ unconnected layers
    if len(unconnected.shape) == 2:
        # OpenCV รุ่นเก่า
        output_layers = [layer_names[i[0] - 1] for i in unconnected]
    else:
        # OpenCV รุ่นใหม่
        output_layers = [layer_names[i - 1] for i in unconnected]
    
    print(f"Loaded {len(output_layers)} output layers")
    return net, classes, output_layers

# ฟังก์ชันตรวจจับรถ
def detect_vehicles(frame, net, output_layers, classes):
    height, width, channels = frame.shape
    
    # เตรียมข้อมูลสำหรับ YOLO
    blob = cv2.dnn.blobFromImage(frame, 0.00392, BLOB_INPUT_SIZE, (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outputs = net.forward(output_layers)
    
    # ข้อมูลสำหรับ bounding boxes, confidences, class_ids
    boxes = []
    confidences = []
    class_ids = []
    
    # วิเคราะห์ผลลัพธ์
    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            
            # กรองเฉพาะรถยนต์ (class_id: 2=car, 5=bus, 7=truck)
            if confidence > 0.5 and class_id in [2, 5, 7]:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)
    
    # Non-maximum suppression
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    
    # วาด bounding boxes
    if len(indexes) > 0:
        for i in indexes.flatten():
            x, y, w, h = boxes[i]
            label = str(classes[class_ids[i]])
            confidence = confidences[i]
            
            color = (0, 255, 0)  # สีเขียว
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, f"{label} {confidence:.2f}", (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return frame, len(indexes) if len(indexes) > 0 else 0

# ฟังก์ชันรับ video stream จาก ESP32-CAM
def get_frame_from_esp32():
    try:
        # ลองเชื่อมต่อหลายครั้ง
        for attempt in range(3):
            try:
                # เพิ่ม read timeout ให้ยาวขึ้น เพราะ MJPEG stream อาจใช้เวลาส่งเฟรมแรก
                stream = requests.get(ESP32_CAM_URL, stream=True, timeout=(3, 15))
                if stream.status_code == 200:
                    bytes_data = bytes()
                    for chunk in stream.iter_content(chunk_size=1024):
                        bytes_data += chunk
                        a = bytes_data.find(b'\xff\xd8')  # JPEG start
                        b = bytes_data.find(b'\xff\xd9')  # JPEG end
                        
                        if a != -1 and b != -1:
                            jpg = bytes_data[a:b+2]
                            bytes_data = bytes_data[b+2:]
                            
                            # แปลง bytes เป็น image
                            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if frame is not None:
                                return frame
                break
            except requests.exceptions.RequestException:
                if attempt < 2:  # ไม่ใช่ครั้งสุดท้าย
                    time.sleep(1)  # รอ 1 วินาทีก่อนลองใหม่
                    continue
                else:
                    raise
    except Exception as e:
        print(f"Error getting frame: {e}")
    return None

# ทางเลือกสำรอง: ใช้ OpenCV เปิดสตรีม MJPEG ตรง ๆ
def get_frame_via_opencv():
    try:
        cap = getattr(get_frame_via_opencv, "_cap", None)
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(ESP32_CAM_URL)
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
            get_frame_via_opencv._cap = cap
        ret, frame = cap.read()
        if ret and frame is not None:
            return frame
    except Exception as e:
        print(f"OpenCV stream error: {e}")
    return None

# ฟังก์ชันทดสอบการเชื่อมต่อ ESP32-CAM
def test_esp32_connection():
    print(f"Testing connection to ESP32-CAM at: {ESP32_CAM_URL}")
    try:
        # ใช้ stream=True เพื่อไม่อ่านเนื้อหา MJPEG ทั้งหมด (ซึ่งไม่มีวันจบ)
        response = requests.get(
            ESP32_CAM_URL,
            stream=True,
            timeout=(3, 5),
            headers={"Accept": "multipart/x-mixed-replace"},
        )
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "multipart/x-mixed-replace" in content_type:
                print("✓ ESP32-CAM connection successful!")
                return True
            else:
                print(f"✗ Unexpected Content-Type: {content_type}")
                return False
        else:
            print(f"✗ ESP32-CAM returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to ESP32-CAM: {e}")
        print("Please check:")
        print("1. ESP32-CAM is powered on")
        print("2. ESP32-CAM is connected to WiFi")
        print("3. IP address is correct")
        print("4. Both devices are on the same network")
        return False

def main():
    print("Starting vehicle detection system...")
    
    # โหลด YOLO model
    try:
        net, classes, output_layers = load_yolo()
        print("YOLO model loaded successfully!")
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        print("Please download yolov4.weights, yolov4.cfg, and coco.names files")
        return
    
    # ทดสอบการเชื่อมต่อ ESP32-CAM
    if not test_esp32_connection():
        print("Continuing anyway... (will show connection error screen)")
    
    # สร้างหน้าต่างแสดงผล
    cv2.namedWindow('Vehicle Detection', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Vehicle Detection', 800, 600)
    
    frame_count = 0
    error_count = 0
    
    while True:
        # รับ frame จาก ESP32-CAM
        frame = get_frame_from_esp32()
        if frame is None:
            # ลองทางเลือกสำรองด้วย OpenCV หากการอ่านผ่าน requests ล้มเหลว
            frame = get_frame_via_opencv()
        
        if frame is not None:
            frame_count += 1
            error_count = 0  # รีเซ็ต error count เมื่อได้ frame สำเร็จ
            
            # ตรวจจับรถ เฉพาะบางเฟรมเพื่อลดภาระ CPU/GPU
            if frame_count % PROCESS_EVERY_N == 0:
                try:
                    processed_frame, vehicle_count = detect_vehicles(frame, net, output_layers, classes)
                    last_processed = processed_frame
                    last_count = vehicle_count
                except Exception as e:
                    print(f"Detection error: {e}")
                    processed_frame = frame
                    vehicle_count = 0
            else:
                processed_frame = locals().get('last_processed', frame)
                vehicle_count = locals().get('last_count', 0)
            
            # แสดงจำนวนรถที่ตรวจพบ
            cv2.putText(processed_frame, f"Vehicles detected: {vehicle_count}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(processed_frame, f"Frame: {frame_count}", 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # แสดงผล
            cv2.imshow('Vehicle Detection', processed_frame)
        else:
            error_count += 1
            # แสดงข้อความเมื่อไม่สามารถรับ frame ได้
            blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(blank_frame, "No connection to ESP32-CAM", 
                       (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(blank_frame, f"Retrying... ({error_count})", 
                       (150, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(blank_frame, "Press 'q' to quit", 
                       (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow('Vehicle Detection', blank_frame)
            
            # ถ้า error มากเกินไป ให้รอสักครู่
            if error_count > 10:
                time.sleep(2)
        
        # กด 'q' เพื่อออก
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()