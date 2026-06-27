import cv2
import time

def draw_hud(frame):
    # Рисуем "радар" или статусную панель в углу
    height, width, _ = frame.shape
    
    # Прямоугольник для интерфейса
    cv2.rectangle(frame, (20, 20), (300, 100), (0, 0, 0), -1) # Черная подложка
    
    # Текст статуса
    cv2.putText(frame, "SYSTEM: AR_MODE_ON", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(frame, f"FPS: {int(1/dt)}", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

# Инициализация
cap = cv2.VideoCapture(0)
prev_time = 0

while True:
    ret, frame = cap.read()
    if not ret: break

    # Вычисляем время кадра для FPS
    curr_time = time.time()
    dt = curr_time - prev_time
    prev_time = curr_time

    # Отрисовываем интерфейс
    draw_hud(frame)

    cv2.imshow('Smart Glasses Simulation', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()