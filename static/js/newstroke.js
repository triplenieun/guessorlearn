const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const agreeButton = document.getElementById('agreeButton');
const disagreeButton = document.getElementById('disagreeButton');
const clearButton = document.getElementById('clearButton');

ctx.imageSmoothingEnabled = false; 
let drawing = false;
let strokes = [];

let currentStroke = [];
let currentStrokeX = [];
let currentStrokeY = [];

let best_prob;
let best_label;

const color_list = ['red', 'orange', 'yellow', 'green', 'blue', 'navy', 'purple', 'brown', 'gray', 'black'];
let drawing_color;
let drawing_color_idx;
let used_color_list = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

// drawing 색깔 설정
const color_blocks = document.getElementsByClassName('color-block');
for (let i = 0; i < color_blocks.length; i++) {
    color_blocks[i].addEventListener('click', () => {
        drawing_color = color_list[i];
        drawing_color_idx = i;
    })
}

// 배경을 흰색으로 설정
function fillCanvasBackgroundWithWhite() {
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}

fillCanvasBackgroundWithWhite();

// 그림 표시 및 좌표 저장
function saveCoord(x, y) {
    currentStrokeX.push(parseInt(x));
    currentStrokeY.push(parseInt(y));
}

function startDrawing(event) {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    saveCoord(parseInt(x), parseInt(y));

    drawing = true;
    draw(event);
}

function stopDrawing() {
    drawing = false;

    currentStroke.push(currentStrokeX);
    currentStroke.push(currentStrokeY);
    strokes.push(currentStroke)

    if (currentStrokeX.length == 0 && currentStrokeY.length == 0) {
        
    } else {
        prediction();
    }

    currentStrokeX = [];
    currentStrokeY = [];
    currentStroke = [];
    ctx.beginPath();
}

function draw(event) {
    if (!drawing) return;
    ctx.lineWidth = 3;
    ctx.lineCap = 'butt';
    ctx.strokeStyle = drawing_color;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    let lastX = currentStrokeX[currentStrokeX.length - 1];
    let lastY = currentStrokeY[currentStrokeY.length - 1];
    if (lastX != parseInt(x) && lastY != parseInt(y))
        saveCoord(parseInt(x), parseInt(y));

    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);

    used_color_list[drawing_color_idx] = 1;
}

function startTouch(event) {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const x = event.touches[0].clientX - rect.left;
    const y = event.touches[0].clientY - rect.top;
    
    saveCoord(parseInt(x), parseInt(y));

    drawing = true;
    touch(event);
}

function stopTouch() {
    drawing = false;

    currentStroke.push(currentStrokeX);
    currentStroke.push(currentStrokeY);
    strokes.push(currentStroke)

    currentStrokeX = [];
    currentStrokeY = [];
    currentStroke = [];
    ctx.beginPath();
    
    prediction();
}

function touch(event) {
    if (!drawing) return;
    ctx.lineWidth = 3;
    ctx.lineCap = 'butt';
    ctx.strokeStyle = drawing_color;

    const rect = canvas.getBoundingClientRect();
    const x = event.touches[0].clientX - rect.left;
    const y = event.touches[0].clientY - rect.top;

    let lastX = currentStrokeX[currentStrokeX.length - 1];
    let lastY = currentStrokeY[currentStrokeY.length - 1];
    if (lastX != parseInt(x) && lastY != parseInt(y))
        saveCoord(parseInt(x), parseInt(y));

    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);

    used_color_list[drawing_color_idx] = 1;
}

canvas.addEventListener('mousedown', startDrawing);
canvas.addEventListener('mouseup', stopDrawing);
canvas.addEventListener('mouseout', stopDrawing);
canvas.addEventListener('mousemove', draw);

canvas.addEventListener('touchstart', startTouch);
canvas.addEventListener('touchend', stopTouch);
canvas.addEventListener('touchmove', touch);

// 좌표 시퀀스 데이터 출력
function prediction() {
    // 여기에 데이터를 서버로 전송하거나 로컬에 저장하는 코드를 추가할 수 있습니다.
    // console.log(JSON.stringify({'strokes': strokes, 'used_color_list': used_color_list}))
    fetch('/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({'strokes': strokes, 'used_color_list': used_color_list})
    })
    .then(response => response.json())
    .then(data => {
        // console.log(data.eng_label); // 서버 응답 출력
        // console.log(data.value);
        best_prob = data.value[0];
        best_label = data.eng_label[0];
        const btn_gauge_sets = document.getElementsByClassName('btn-gauge-set');
        for (let i = 0; i < btn_gauge_sets.length; i++) {
            btn_gauge_sets[i].classList.remove('invisible');
        }
        const label0 = document.getElementById('label0');
        label0.innerHTML = "<span style='font-weight: bold;'>" + data.kor_label[0] + "</span>(" + data.eng_label[0] + "): <span style='font-weight: bold;'>" + data.value[0].toFixed(3) + "%</span>";

        const label1 = document.getElementById('label1');
        label1.innerHTML = "<span style='font-weight: bold;'>" + data.kor_label[1] + "</span>(" + data.eng_label[1] + "): <span style='font-weight: bold;'>" + data.value[1].toFixed(3) + "%</span>";

        const label2 = document.getElementById('label2');
        label2.innerHTML = "<span style='font-weight: bold;'>" + data.kor_label[2] + "</span>(" + data.eng_label[2] + "): <span style='font-weight: bold;'>" + data.value[2].toFixed(3) + "%</span>";

        const label3 = document.getElementById('label3');
        label3.innerHTML = "<span style='font-weight: bold;'>" + data.kor_label[3] + "</span>(" + data.eng_label[3] + "): <span style='font-weight: bold;'>" + data.value[3].toFixed(3) + "%</span>";

        const label4 = document.getElementById('label4');
        label4.innerHTML = "<span style='font-weight: bold;'>" + data.kor_label[4] + "</span>(" + data.eng_label[4] + "): <span style='font-weight: bold;'>" + data.value[4].toFixed(3) + "%</span>";

        // const btn5 = document.getElementById('label-btn5');
        // btn5.classList.remove('invisible');        
        // btn5.value = 'Teach AI the answer.';

        document.getElementById('gauge0').value = data.value[0];
        document.getElementById('gauge1').value = data.value[1];
        document.getElementById('gauge2').value = data.value[2];
        document.getElementById('gauge3').value = data.value[3];
        document.getElementById('gauge4').value = data.value[4];
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// 그림 및 리스트 초기화
function clearData(recog) {
    strokes = [];
    currentStroke = [];
    fillCanvasBackgroundWithWhite();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    fillCanvasBackgroundWithWhite();
    used_color_list = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

    const btn_gauge_sets = document.getElementsByClassName('btn-gauge-set');
    for (let i = 0; i < btn_gauge_sets.length; i++) {
        btn_gauge_sets[i].classList.add('invisible');
    }

    if (recog) {
        fetch('/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(best_label)
        })
        .then(response => response.json())
        .then(data => {
    
        })
        .catch(error => {
            console.error('Error:', error);
        });
    } else {
        fetch('/savefalse', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(best_label)
        })
        .then(response => response.json())
        .then(data => {
            
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
}

agreeButton.addEventListener('click', () => {
    clearData(true);
});
disagreeButton.addEventListener('click', () => {
    clearData(false);
});
clearButton.addEventListener('click', () => {
    clearData(true);
});

document.querySelector('.black-bg').addEventListener('click', () => {
    document.querySelector('.black-bg').classList.add('invisible');
})


// 그림 추천
enLabel = ['The Eiffel Tower', 'The Great Wall', 'The Mona Lisa', 'aircraft carrier', 'airplane', 'alarm clock', 'ambulance', 'angel', 'ant', 'anvil', 'apple', 'arm', 'asparagus', 'axe', 'backpack', 'banana', 'bandage', 'barn', 'baseball bat', 'baseball', 'basket', 'basketball', 'bat', 'bathtub', 'beach', 'bear', 'beard', 'bed', 'bee', 'belt', 'bench', 'bicycle', 'binoculars', 'bird', 'blackberry', 'book', 'boomerang', 'bottlecap', 'bowtie', 'bracelet', 'brain', 'bread', 'bridge', 'broccoli', 'broom', 'bucket', 'bus', 'bush', 'butterfly', 'cactus', 'cake', 'calculator', 'calendar', 'camel', 'camera', 'campfire', 'candle', 'cannon', 'canoe', 'car', 'carrot', 'castle', 'cat', 'ceiling fan', 'cell phone', 'cello', 'chair', 'chandelier', 'church', 'circle', 'clarinet', 'clock', 'cloud', 'compass', 'computer', 'cookie', 'cooler', 'couch', 'cow', 'crab', 'crayon', 'crocodile', 'crown', 'cruise ship', 'cup', 'diamond', 'dishwasher', 'diving board', 'dog', 'dolphin', 'donut', 'door', 'dragon', 'dresser', 'drill', 'drums', 'duck', 'dumbbell', 'ear', 'elbow', 'elephant', 'envelope', 'eraser', 'eye', 'eyeglasses', 'face', 'fan', 'feather', 'fence', 'finger', 'fire hydrant', 'fireplace', 'firetruck', 'fish', 'flamingo', 'flashlight', 'flip flops', 'floor lamp', 'flower', 'flying saucer', 'foot', 'fork', 'frog', 'frying pan', 'garden hose', 'giraffe', 'golf club', 'grapes', 'grass', 'guitar', 'hamburger', 'hammer', 'hand', 'harp', 'hat', 'headphones', 'hedgehog', 'helicopter', 'helmet', 'hexagon', 'hockey puck', 'hockey stick', 'horse', 'hospital', 'hot air balloon', 'hot dog', 'hourglass', 'house plant', 'house', 'ice cream', 'jacket', 'jail', 'kangaroo', 'key', 'keyboard', 'knee', 'knife', 'ladder', 'lantern', 'laptop', 'leaf', 'leg', 'light bulb', 'lighter', 'lighthouse', 'lightning', 'line', 'lion', 'lipstick', 'lobster', 'lollipop', 'mailbox', 'map', 'matches', 'megaphone', 'mermaid', 'microphone', 'microwave', 'monkey', 'moon', 'mosquito', 'motorbike', 'mountain', 'mouse', 'moustache', 'mouth', 'mushroom', 'necklace', 'nose', 'ocean', 'octagon', 'octopus', 'onion', 'oven', 'owl', 'paint can', 'paintbrush', 'palm tree', 'panda', 'pants', 'paper clip', 'parachute', 'parrot', 'passport', 'peanut', 'pear', 'peas', 'pencil', 'penguin', 'piano', 'picture frame', 'pig', 'pillow', 'pineapple', 'pizza', 'pliers', 'police car', 'pond', 'pool', 'popsicle', 'postcard', 'potato', 'power outlet', 'purse', 'rabbit', 'raccoon', 'radio', 'rain', 'rainbow', 'rake', 'remote control', 'rhinoceros', 'rifle', 'river', 'roller coaster', 'rollerskates', 'sailboat', 'sandwich', 'saw', 'saxophone', 'scissors', 'scorpion', 'screwdriver', 'sea turtle', 'see saw', 'shark', 'sheep', 'shoe', 'shorts', 'shovel', 'sink', 'skateboard', 'skull', 'skyscraper', 'sleeping bag', 'smiley face', 'snail', 'snake', 'snorkel', 'snowflake', 'snowman', 'soccer ball', 'sock', 'speedboat', 'spider', 'spoon', 'spreadsheet', 'square', 'squirrel', 'stairs', 'star', 'steak', 'stereo', 'stethoscope', 'stitches', 'stop sign', 'stove', 'strawberry', 'streetlight', 'submarine', 'suitcase', 'sun', 'swan', 'sweater', 'swing set', 'sword', 'syringe', 't-shirt', 'table', 'teapot', 'teddy-bear', 'telephone', 'television', 'tennis racquet', 'tent', 'tiger', 'toaster', 'toe', 'toilet', 'tooth', 'toothbrush', 'toothpaste', 'tornado', 'tractor', 'traffic light', 'train', 'tree', 'triangle', 'trombone', 'truck', 'trumpet', 'umbrella', 'underwear', 'van', 'vase', 'violin', 'washing machine', 'watermelon', 'waterslide', 'whale', 'wheel', 'windmill', 'wine bottle', 'wine glass', 'wristwatch', 'yoga', 'zebra', 'zigzag']

koLabel =  ['에펠탑', '만리장성', '모나리자', '항공모함', '비행기', '알람 시계', '구급차', '천사', '개미', '모루', '사과', '팔', '아스파라거스', '도끼', '배낭', '바나나', '붕대', '헛간', '야구 방망이', '야구', '바구니', '농구', '박쥐', '욕조', '해변', '곰', '턱수염', '침대', '벌', '벨트', '벤치', '자전거', '쌍안경', '새', '블랙베리', '책', '부메랑', '병뚜껑', '나비 넥타이', '팔찌', '뇌', '빵', '다리', '브로콜리', '빗자루', '양동이', '버스', '덤불', '나비', '선인장', '케이크', '계산기', '달력', '낙타', '카메라', '모닥불', '양초', '대포', '카누', '자동차', '당근', '성', '고양이', '천장 선풍기', '휴대폰', '첼로', '의자', '샹들리에', '교회', '원', '클라리넷', '시계', '구름', '나침반', '컴퓨터', '쿠키', '쿨러', '소파', '소', '게', '크레용', '악어', '왕관', '유람선', '컵', '다이아몬드', '식기 세척기', '다이빙 보드', '개', '돌고래', '도넛', '문', '용', '옷장', '드릴', '드럼', '오리', '덤벨', '귀', '팔꿈치', '코끼리', '봉투', '지우개', '눈', '안경', '얼굴', '선풍기', '깃털', '울타리', '손가락', '소화전', '벽난로', '소방차', '물고기', '플라밍고', '손전등', '샌들', '플로어 램프', '꽃', '우주선', '발', '포크', '개구리', '프라이팬', '정원 호스', '기린', '골프 클럽', '포도', '잔디', '기타', '햄버거', '망치', '손', '하프', '모자', '헤드폰', '고슴도치', '헬리콥터', '헬멧', '육각형', '하키 퍽', '하키 스틱', '말', '병원', '열기구', '핫도그', '모래시계', '실내 식물', '집', '아이스크림', '재킷', '감옥', '캥거루', '열쇠', '키보드', '무릎', '칼', '사다리', '랜턴', '노트북', '잎', '다리', '전구', '라이터', '등대', '번개', '선', '사자', '립스틱', '바닷가재', '막대 사탕', '우편함', '지도', '성냥', '메가폰', '인어', '마이크', '전자레인지', '원숭이', '달', '모기', '오토바이', '산', '쥐', '콧수염', '입', '버섯', '목걸이', '코', '바다', '팔각형', '문어', '양파', '오븐', '올빼미', '페인트 캔', '붓', '야자수', '팬더', '바지', '종이 클립', '낙하산', '앵무새', '여권', '땅콩', '배', '완두콩', '연필', '펭귄', '피아노', '액자', '돼지', '베개', '파인애플', '피자', '펜치', '경찰차', '연못', '수영장', '아이스크림', '엽서', '감자', '전원 콘센트', '지갑', '토끼', '너구리', '라디오', '비', '무지개', '갈퀴', '리모컨', '코뿔소', '소총', '강', '롤러코스터', '롤러스케이트', '범선', '샌드위치', '톱', '색소폰', '가위', '전갈', '드라이버', '바다거북', '시소', '상어', '양', '신발', '반바지', '삽', '싱크대', '스케이트보드', '해골', '마천루', '침낭', '스마일', '달팽이', '뱀', '스노클', '눈송이', '눈사람', '축구공', '양말', '스피드보트', '거미', '숟가락', '스프레드시트', '정사각형', '다람쥐', '계단', '별', '스테이크', '스테레오', '청진기', '바늘', '정지 신호', '난로', '딸기', '가로등', '잠수함', '여행 가방', '태양', '백조', '스웨터', '그네', '칼', '주사기', '티셔츠', '테이블', '찻주전자', '곰인형', '전화기', '텔레비전', '테니스 라켓', '텐트', '호랑이', '토스터', '발가락', '화장실', '치아', '칫솔', '치약', '토네이도', '트랙터', '신호등', '기차', '나무', '삼각형', '트롬본', '트럭', '트럼펫', '우산', '속옷', '승합차', '꽃병', '바이올린', '세탁기', '수박', '워터슬라이드', '고래', '바퀴', '풍차', '와인 병', '와인 잔', '손목시계', '요가', '얼룩말', '지그재그']

function recommend() {
    const rand1 = Math.floor(Math.random() * 328);
    const rand2 = Math.floor(Math.random() * 328);
    const rand3 = Math.floor(Math.random() * 328);
    document.getElementById('drawing-recommendation').innerHTML = "<p style='margin: 0; font-size: 25px;'>음... <span style='font-weight: bold;'>" + koLabel[rand1] + "</span> 또는 <span style='font-weight: bold;'>" + koLabel[rand2] + "</span>, <span style='font-weight: bold;'>" + koLabel[rand3] + "</span>을(를) 그려 보는 건 어때요?</p><p style='margin: 0;'>Hmm... It might be nice to try sketching <span style='font-weight: bold;'>" + enLabel[rand1] + "</span> or <span style='font-weight: bold;'>" + enLabel[rand2] + "</span> or <span style='font-weight: bold;'>" + enLabel[rand3] + "</span>?</p>"
}

window.addEventListener('load', recommend);
agreeButton.addEventListener('click', recommend);
disagreeButton.addEventListener('click', recommend);