# ESP32‑CAM Vehicle Detection (YOLOv4 + OpenCV)

ระบบตรวจจับยานพาหนะแบบเรียลไทม์จากสตรีมของ ESP32‑CAM และประมวลผลด้วย YOLOv4 บนเครื่องคอมพิวเตอร์ (macOS/Linux/Windows)

## โครงสร้างโปรเจกต์
```
cam-new/
├── main.ino                # โค้ดสำหรับอัปโหลดลง ESP32‑CAM
├── vehicle_detection.py    # โค้ด Python ตรวจจับรถจากสตรีม
├── requirements.txt        # รายการไลบรารี Python
├── coco.names              # รายการชื่อคลาส COCO
└── (ดาวน์โหลด) yolov4.cfg, yolov4.weights
```

## สิ่งที่ต้องมี
- Arduino IDE (หรือตัวเลือกอื่นสำหรับแฟลชบอร์ด ESP32)
- Python 3.10 – 3.12 และ pip
- ESP32‑CAM + บอร์ดอัปโหลด (เช่น ESP32‑CAM‑MB)
- เครือข่าย Wi‑Fi เดียวกันระหว่างคอมพิวเตอร์และ ESP32‑CAM

## ขั้นตอนที่ 1: เตรียม ESP32‑CAM
1) เปิด Arduino IDE และติดตั้งบอร์ด ESP32 (Boards Manager ค้นหา “ESP32” แล้วติดตั้งจาก Espressif Systems)
2) เปิดไฟล์ `main.ino`
3) เปลี่ยนค่า Wi‑Fi SSID/Password ให้ถูกต้องในไฟล์ (ตัวแปร `ssid`, `password`)
4) อัปโหลดไปที่ ESP32‑CAM
5) เปิด Serial Monitor เพื่อดู IP ที่ได้รับ และจด IP นั้นไว้ (เช่น `192.168.137.80`)

หมายเหตุ: สเก็ตช์นี้เปิดสตรีมที่เส้นทาง `/stream` และพอร์ต 80 ดังนั้น URL จะเป็น `http://<IP>/stream`

## ขั้นตอนที่ 2: เตรียมสภาพแวดล้อม Python
1) สร้างและเปิดใช้งาน virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# หรือบน Windows: .venv\Scripts\activate
```
2) ติดตั้งไลบรารี
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
3) ดาวน์โหลดไฟล์โมเดล YOLOv4 (เก็บไว้ในโฟลเดอร์เดียวกับ `vehicle_detection.py`)
```bash
# cfg
curl -O https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4.cfg
# weights (~246MB)
wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v3_optimal/yolov4.weights
```

## ขั้นตอนที่ 3: ตั้งค่าและรัน
1) เปิดไฟล์ `vehicle_detection.py` แล้วแก้บรรทัด IP ให้ตรงกับบอร์ดของคุณ
```python
ESP32_CAM_URL = "http://<IP-ของคุณ>/stream"
```
2) รันสคริปต์
```bash
python3 vehicle_detection.py
```
- กด `q` เพื่อปิดหน้าต่างแสดงผล

## การปรับแต่งประสิทธิภาพ
- ใน `vehicle_detection.py` มีตัวแปร
  - `PROCESS_EVERY_N` เพื่อตรวจจับทุก ๆ N เฟรม ลดอาการค้างเมื่อโหลดสูง
  - `BLOB_INPUT_SIZE` เพื่อปรับขนาดอินพุตของ YOLO (เช่น 320x320 จะเร็วขึ้นกว่าค่า 416x416)
- ใน `main.ino` สามารถลดความละเอียดกล้อง (เช่น `FRAMESIZE_QVGA`) เพื่อลดภาระเครือข่าย/ประมวลผล

## แก้ปัญหาเบื้องต้น
- เปิดได้ในเบราว์เซอร์แต่ Python ต่อไม่ติด:
  - ปิดแท็บเบราว์เซอร์ที่เปิด `/stream` (เชื่อมต่อพร้อมกันได้จำกัด)
  - ตรวจสอบ Firewall ของ macOS ให้อนุญาต Terminal/Python ออกเน็ตภายใน
- ถ้าสตรีมช้า/ค้างเมื่อเริ่มตรวจจับ:
  - เพิ่ม `PROCESS_EVERY_N` หรือปรับ `BLOB_INPUT_SIZE` ให้เล็กลง
  - ลดความละเอียดกล้องใน `main.ino`
- ข้อจำกัดขนาดไฟล์บน GitHub: ไฟล์ `yolov4.weights` มีขนาด >100MB จึงไม่ได้เก็บในรีโป ให้ดาวน์โหลดตามคำสั่งด้านบน

## ใบอนุญาต
โปรเจกต์นี้ใช้สำหรับการศึกษา/ทดลอง ใช้โมเดล YOLOv4 จากแหล่งโอเพ่นซอร์ส โปรดปฏิบัติตามเงื่อนไขของผู้พัฒนาโมเดลต้นทางเมื่อใช้งานเชิงพาณิชย์
