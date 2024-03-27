import cv2
import numpy as np

# Load pre-trained classifiers for detecting faces, eyes, and smiles
face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
smile_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

# Load the pre-trained models for age prediction
age_net = cv2.dnn.readNetFromCaffe(
    'deploy_age.prototxt', 
    'age_net.caffemodel'
)
AGE_LIST = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)', '(38-43)', '(48-53)', '(60-100)']

# Initialize camera
cap = cv2.VideoCapture(0)

# Function to get the most frequent detection from a list
def get_most_frequent(detections):
    if len(detections) == 0:
        return None
    counts = {}
    for detection in detections:
        detection_tuple = tuple(map(tuple, detection))
        counts[detection_tuple] = counts.get(detection_tuple, 0) + 1
    most_frequent = max(counts, key=counts.get)
    return np.array(most_frequent)

# Lists to store recent detections
recent_eyes = []
recent_smiles = []
recent_ages = []

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()
    
    # Convert frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces in the frame
    faces = face_classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    # Process each detected face
    for (x, y, w, h) in faces:
        # Draw rectangles around detected faces
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        cv2.putText(frame, 'Face', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
        
        # Get the region of interest (ROI) for eyes within the face rectangle
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]
        
        # Detect eyes within the face region
        eyes = eye_classifier.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=10)
        if len(eyes) > 0:
            recent_eyes.append(eyes)
            if len(recent_eyes) > 10:
                recent_eyes.pop(0)
        
        stable_eyes = get_most_frequent(recent_eyes)
        if stable_eyes is not None:
            for (ex, ey, ew, eh) in stable_eyes:
                # Draw rectangles around detected eyes
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)
                cv2.putText(frame, 'Eye', (x + ex, y + ey - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Detect smiles within the face region
        smiles = smile_classifier.detectMultiScale(roi_gray, scaleFactor=1.8, minNeighbors=20)
        if len(smiles) > 0:
            recent_smiles.append(smiles)
            if len(recent_smiles) > 10:
                recent_smiles.pop(0)
        
        stable_smiles = get_most_frequent(recent_smiles)
        if stable_smiles is not None:
            for (sx, sy, sw, sh) in stable_smiles:
                # Draw rectangles around detected smiles
                cv2.rectangle(roi_color, (sx, sy), (sx+sw, sy+sh), (0, 0, 255), 2)
                cv2.putText(frame, 'Smile', (x + sx, y + sy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Prepare the face ROI for age prediction
        face_blob = cv2.dnn.blobFromImage(roi_color, 1.0, (227, 227), (78.4263377603, 87.7689143744, 114.895847746), swapRB=False)
        age_net.setInput(face_blob)
        age_predictions = age_net.forward()
        age_index = age_predictions[0].argmax()
        age = AGE_LIST[age_index]
        confidence = age_predictions[0][age_index]
        
        # Add the detected age to the list
        recent_ages.append((age, confidence))
        if len(recent_ages) > 10:
            recent_ages.pop(0)
        
        # Get the most frequent age from the list
        stable_age = max(set(recent_ages), key=recent_ages.count)
        
        # Display the estimated age on the frame
        if stable_age:
            display_text = f"{stable_age[0]} ({stable_age[1]*100:.2f}%)"
            cv2.putText(frame, display_text, (x, y + h + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    
    # Display the resulting frame
    cv2.imshow('Face Detection with Age Estimation', frame)
    
    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the camera and close OpenCV windows
cap.release()
cv2.destroyAllWindows()
