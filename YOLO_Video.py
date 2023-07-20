def deteksi_realtime():
    import cv2
    from datetime import datetime
    import mysql.connector
    from ultralytics import YOLO
    import time
    import torch

    model_path = 'model/best.pt'

    # Load a model
    model = YOLO(model_path)  # load a custom model

    threshold = 0.5

    class_name_dict = {0: 'rokok', 1: 'orang'}

    # ip = 'http://192.168.237.110:4747/video'
    # video = 'D:/smt 6/BIGPRO/flask app/tes.mp4'
    # cap = cv2.VideoCapture(ip)
    cap = cv2.VideoCapture(1)  #camera
    if not cap.isOpened():
        raise IOError("Cannot open webcam")

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="deteksimerokok"
    )

    cursor = db.cursor()

    interval = 5
    number = 0
    start_time = time.time()
    current_time = time.time()
    elapsed_time = current_time - start_time

    circle_detected = False
    circle_center = ()
    circle_radius = 0
    rectangle_detected = False
    rectangle_top_left = ()
    rectangle_bottom_right = ()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        H, W, _ = frame.shape

        results = model(frame, device=torch.device('cuda'))[0]

        for result in results.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = result
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if score > threshold:
                if class_id == 0:
                    # Circle (Rokok) detected
                    circle_detected = True
                    circle_center = ((x1 + x2) // 2, (y1 + y2) // 2)
                    circle_radius = (x2 - x1) // 8
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 4)
                    cv2.circle(frame, (int(circle_center[0]), int(circle_center[1])), int(circle_radius), (0, 0, 255), -1)
                    cv2.putText(frame, class_name_dict[class_id].upper(), (int(x1), int(y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 255), 3, cv2.LINE_AA)

                elif class_id == 1:
                    # Rectangle (Orang) detected
                    rectangle_detected = True
                    rectangle_top_left = (int(x1), int(y1))
                    rectangle_bottom_right = (int(x2), int(y2))
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 4)
                    cv2.putText(frame, class_name_dict[class_id].upper(), (int(x1), int(y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3, cv2.LINE_AA)

        if circle_detected and rectangle_detected:
            # Check if the circle and rectangle intersect
            if (circle_center[0] - circle_radius <= rectangle_bottom_right[0] and
                    circle_center[0] + circle_radius >= rectangle_top_left[0] and
                    circle_center[1] - circle_radius <= rectangle_bottom_right[1] and
                    circle_center[1] + circle_radius >= rectangle_top_left[1]):
                # Intersection detected
                # Capture and store the data
                if number == 0:
                    number += 1
                    data = (timestamp, 'Terdeteksi Merokok')
                    query = "INSERT INTO data (waktu, kondisi) VALUES (%s, %s)"
                    cursor.execute(query, data)
                    db.commit()
                    if number >= 1:
                        if elapsed_time >= interval:
                            start_time = time.time()
                            number = 0

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cv2.destroyAllWindows()
