def frame_detect():
    import cv2
    from datetime import datetime
    import mysql.connector
    from ultralytics import YOLO
    import time

    model_path = 'D:/SEMESTER 6/capstone project smstr 6/yolo/yolov8n.pt'

    model = YOLO(model_path)  # load a custom model

    threshold = 0.5

    class_name_dict = {0: 'mobil', 1: 'bus'}

    video_path = 'D:/SEMESTER 6/capstone project smstr 6/yolo/video.mp4'
    cap = cv2.VideoCapture(video_path)  # use default camera
    if not cap.isOpened():
        raise IOError("Cannot open video")

    cv2.namedWindow('Real-time Detection', cv2.WINDOW_NORMAL)

    # Set up line parameters
    line_position = 650  # garis hitung
    line_thickness = 2
    line_color = (0, 255, 0)

    jumlah = 0
    vehicle_passed = set()

    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="webservice"
    )
    mycursor = mydb.cursor()

    start_time = time.time()
    interval = 60  # 1 minute

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        H, W, _ = frame.shape

        results = model(frame)[0]

        for result in results.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = result

            if score > threshold:
                if class_id == 0:
                    class_label = ''
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 4)
                    cv2.circle(frame, (int((x1 + x2) / 2), int((y1 + y2) / 2)), 5, (0, 0, 255), -1)  # Titik Merah
                    cv2.putText(frame, class_label.upper(), (int(x1), int(y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 255), 3, cv2.LINE_AA)

                    # Check if vehicle passes the counting line
                    if int((y1 + y2) / 2) > line_position and int((y1 + y2) / 2) not in vehicle_passed:
                        jumlah += 1
                        vehicle_passed.add(int((y1 + y2) / 2))

                else:
                    class_label = ''
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 4)
                    cv2.circle(frame, (int((x1 + x2) / 2), int((y1 + y2) / 2)), 5, (0, 0, 255), -1)  # Titik Merah
                    cv2.putText(frame, class_label.upper(), (int(x1), int(y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3, cv2.LINE_AA)

                    # Check if vehicle passes the counting line
                    if int((y1 + y2) / 2) > line_position and int((y1 + y2) / 2) not in vehicle_passed:
                        jumlah += 1
                        vehicle_passed.add(int((y1 + y2) / 2))

        cv2.line(frame, (0, line_position), (W, line_position), line_color, line_thickness)

        cv2.putText(frame, f"Jumlah kendaraan: {jumlah}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        if jumlah <= 50:
            Kepadatan = "Lancar"
        elif jumlah <= 100:
            Kepadatan = "Padat"
        else:
            Kepadatan = "Macet"

        cv2.putText(frame, f"Kepadatan: {Kepadatan}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow('Real-time Detection', frame)

        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time >= interval:
            sql = "INSERT INTO detek (waktu_awal, waktu_akhir, jumlah, kategori) VALUES (%s, %s, %s, %s)"
            val = (timestamp, timestamp, jumlah, Kepadatan)
            mycursor.execute(sql, val)
            mydb.commit()

            # Reset hitung jumlah
            jumlah = 0
            vehicle_passed = set()

            # Reset timer
            start_time = time.time()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Close the database connection and release the video capture
    mycursor.close()
    mydb.close()
    cap.release()
    cv2.destroyAllWindows()
