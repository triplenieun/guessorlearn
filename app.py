import os
import datetime
from flask import Flask, request, jsonify, render_template
#from flask_cors import CORS
from model_inference import load_model, predict  # model_inference 파일에서 함수 가져오기
from vector_to_image import transformer_vec_img

app = Flask(__name__)
#CORS(app)
@app.route('/')
def home():
    return render_template('index.html')
    
# 모델 로드
model = load_model()
coordDataString = ""
used_color_list = []

@app.route('/upload', methods=['POST'])
def upload():
    global coordDataString
    global used_color_list
    try:
        data = request.get_json()
        coordData = data['strokes']
        used_color_list = data['used_color_list']
        for i in range(len(coordData)):
            for j in range(len(coordData[i])):
                for k in range(len(coordData[i][j])):
                    coordData[i][j][k] = int(coordData[i][j][k]/2)
        coordDataString = str(coordData)
        img = transformer_vec_img(coordData)

        values, eng_label, kor_label = predict(img, model)
        processed_value = []
        for i in range(5):
            processed_value.append(values[0][i] * 100)
            
        return jsonify({'value': processed_value, 'eng_label': eng_label, 'kor_label': kor_label})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/save', methods=['POST'])
def save():
    global coordDataString
    global used_color_list
    try:
        label_name = request.get_json()
        # drawing 저장
        file_path = os.path.join('static', 'images', 'user_img.txt')
        
        timestamp = datetime.datetime.now()

        with open(file_path, 'a') as f:
            f.write("{\"word\": \"" + str(label_name)+ "\", \"recognized\": true, \"time(UTC)\": \"" + timestamp.strftime('%Y-%m-%d %H:%M:%S') + "\", \"used_colors\": " + str(used_color_list) + ", \"drawing\": " + str(coordDataString) + "}\n")

        return jsonify({'message': "저장 완료"})
    except Exception as e:
        return jsonify({'error': str(e)})
    
@app.route('/savefalse', methods=['POST'])
def savefalse():
    global coordDataString
    global used_color_list
    try:
        label_name = request.get_json()
        file_path = os.path.join('static', 'images', 'user_img.txt')
        
        timestamp = datetime.datetime.now()
        
        with open(file_path, 'a') as f:
            f.write("{\"word\": \"" + str(label_name)+ "\", \"recognized\": false, \"time(UTC)\": \"" + timestamp.strftime('%Y-%m-%d %H:%M:%S') + "\", \"used_colors\": " + str(used_color_list) + ", \"drawing\": " + str(coordDataString) + "}\n")
            
        return jsonify({'message': "저장 완료"})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)