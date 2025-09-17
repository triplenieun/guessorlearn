import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import ResNet

label = ['The Eiffel Tower', 'The Great Wall', 'The Mona Lisa', 'aircraft carrier', 'airplane', 'alarm clock', 'ambulance', 'angel', 'ant', 'anvil', 'apple', 'arm', 'asparagus', 'axe', 'backpack', 'banana', 'bandage', 'barn', 'baseball bat', 'baseball', 'basket', 'basketball', 'bat', 'bathtub', 'beach', 'bear', 'beard', 'bed', 'bee', 'belt', 'bench', 'bicycle', 'binoculars', 'bird', 'blackberry', 'book', 'boomerang', 'bottlecap', 'bowtie', 'bracelet', 'brain', 'bread', 'bridge', 'broccoli', 'broom', 'bucket', 'bus', 'bush', 'butterfly', 'cactus', 'cake', 'calculator', 'calendar', 'camel', 'camera', 'campfire', 'candle', 'cannon', 'canoe', 'car', 'carrot', 'castle', 'cat', 'ceiling fan', 'cell phone', 'cello', 'chair', 'chandelier', 'church', 'circle', 'clarinet', 'clock', 'cloud', 'compass', 'computer', 'cookie', 'cooler', 'couch', 'cow', 'crab', 'crayon', 'crocodile', 'crown', 'cruise ship', 'cup', 'diamond', 'dishwasher', 'diving board', 'dog', 'dolphin', 'donut', 'door', 'dragon', 'dresser', 'drill', 'drums', 'duck', 'dumbbell', 'ear', 'elbow', 'elephant', 'envelope', 'eraser', 'eye', 'eyeglasses', 'face', 'fan', 'feather', 'fence', 'finger', 'fire hydrant', 'fireplace', 'firetruck', 'fish', 'flamingo', 'flashlight', 'flip flops', 'floor lamp', 'flower', 'flying saucer', 'foot', 'fork', 'frog', 'frying pan', 'garden hose', 'giraffe', 'golf club', 'grapes', 'grass', 'guitar', 'hamburger', 'hammer', 'hand', 'harp', 'hat', 'headphones', 'hedgehog', 'helicopter', 'helmet', 'hexagon', 'hockey puck', 'hockey stick', 'horse', 'hospital', 'hot air balloon', 'hot dog', 'hourglass', 'house plant', 'house', 'ice cream', 'jacket', 'jail', 'kangaroo', 'key', 'keyboard', 'knee', 'knife', 'ladder', 'lantern', 'laptop', 'leaf', 'leg', 'light bulb', 'lighter', 'lighthouse', 'lightning', 'line', 'lion', 'lipstick', 'lobster', 'lollipop', 'mailbox', 'map', 'matches', 'megaphone', 'mermaid', 'microphone', 'microwave', 'monkey', 'moon', 'mosquito', 'motorbike', 'mountain', 'mouse', 'moustache', 'mouth', 'mushroom', 'necklace', 'nose', 'ocean', 'octagon', 'octopus', 'onion', 'oven', 'owl', 'paint can', 'paintbrush', 'palm tree', 'panda', 'pants', 'paper clip', 'parachute', 'parrot', 'passport', 'peanut', 'pear', 'peas', 'pencil', 'penguin', 'piano', 'picture frame', 'pig', 'pillow', 'pineapple', 'pizza', 'pliers', 'police car', 'pond', 'pool', 'popsicle', 'postcard', 'potato', 'power outlet', 'purse', 'rabbit', 'raccoon', 'radio', 'rain', 'rainbow', 'rake', 'remote control', 'rhinoceros', 'rifle', 'river', 'roller coaster', 'rollerskates', 'sailboat', 'sandwich', 'saw', 'saxophone', 'scissors', 'scorpion', 'screwdriver', 'sea turtle', 'see saw', 'shark', 'sheep', 'shoe', 'shorts', 'shovel', 'sink', 'skateboard', 'skull', 'skyscraper', 'sleeping bag', 'smiley face', 'snail', 'snake', 'snorkel', 'snowflake', 'snowman', 'soccer ball', 'sock', 'speedboat', 'spider', 'spoon', 'spreadsheet', 'square', 'squirrel', 'stairs', 'star', 'steak', 'stereo', 'stethoscope', 'stitches', 'stop sign', 'stove', 'strawberry', 'streetlight', 'submarine', 'suitcase', 'sun', 'swan', 'sweater', 'swing set', 'sword', 'syringe', 't-shirt', 'table', 'teapot', 'teddy-bear', 'telephone', 'television', 'tennis racquet', 'tent', 'tiger', 'toaster', 'toe', 'toilet', 'tooth', 'toothbrush', 'toothpaste', 'tornado', 'tractor', 'traffic light', 'train', 'tree', 'triangle', 'trombone', 'truck', 'trumpet', 'umbrella', 'underwear', 'van', 'vase', 'violin', 'washing machine', 'watermelon', 'waterslide', 'whale', 'wheel', 'windmill', 'wine bottle', 'wine glass', 'wristwatch', 'yoga', 'zebra', 'zigzag']
koLabel =  ['에펠탑', '만리장성', '모나리자', '항공모함', '비행기', '알람 시계', '구급차', '천사', '개미', '모루', '사과', '팔', '아스파라거스', '도끼', '배낭', '바나나', '붕대', '헛간', '야구 방망이', '야구', '바구니', '농구', '박쥐', '욕조', '해변', '곰', '턱수염', '침대', '벌', '벨트', '벤치', '자전거', '쌍안경', '새', '블랙베리', '책', '부메랑', '병뚜껑', '나비 넥타이', '팔찌', '뇌', '빵', '다리', '브로콜리', '빗자루', '양동이', '버스', '덤불', '나비', '선인장', '케이크', '계산기', '달력', '낙타', '카메라', '모닥불', '양초', '대포', '카누', '자동차', '당근', '성', '고양이', '천장 선풍기', '휴대폰', '첼로', '의자', '샹들리에', '교회', '원', '클라리넷', '시계', '구름', '나침반', '컴퓨터', '쿠키', '쿨러', '소파', '소', '게', '크레용', '악어', '왕관', '유람선', '컵', '다이아몬드', '식기 세척기', '다이빙 보드', '개', '돌고래', '도넛', '문', '용', '옷장', '드릴', '드럼', '오리', '덤벨', '귀', '팔꿈치', '코끼리', '봉투', '지우개', '눈', '안경', '얼굴', '선풍기', '깃털', '울타리', '손가락', '소화전', '벽난로', '소방차', '물고기', '플라밍고', '손전등', '샌들', '플로어 램프', '꽃', '우주선', '발', '포크', '개구리', '프라이팬', '정원 호스', '기린', '골프 클럽', '포도', '잔디', '기타', '햄버거', '망치', '손', '하프', '모자', '헤드폰', '고슴도치', '헬리콥터', '헬멧', '육각형', '하키 퍽', '하키 스틱', '말', '병원', '열기구', '핫도그', '모래시계', '실내 식물', '집', '아이스크림', '재킷', '감옥', '캥거루', '열쇠', '키보드', '무릎', '칼', '사다리', '랜턴', '노트북', '잎', '다리', '전구', '라이터', '등대', '번개', '선', '사자', '립스틱', '바닷가재', '막대 사탕', '우편함', '지도', '성냥', '메가폰', '인어', '마이크', '전자레인지', '원숭이', '달', '모기', '오토바이', '산', '쥐', '콧수염', '입', '버섯', '목걸이', '코', '바다', '팔각형', '문어', '양파', '오븐', '올빼미', '페인트 캔', '붓', '야자수', '팬더', '바지', '종이 클립', '낙하산', '앵무새', '여권', '땅콩', '배', '완두콩', '연필', '펭귄', '피아노', '액자', '돼지', '베개', '파인애플', '피자', '펜치', '경찰차', '연못', '수영장', '아이스크림', '엽서', '감자', '전원 콘센트', '지갑', '토끼', '너구리', '라디오', '비', '무지개', '갈퀴', '리모컨', '코뿔소', '소총', '강', '롤러코스터', '롤러스케이트', '범선', '샌드위치', '톱', '색소폰', '가위', '전갈', '드라이버', '바다거북', '시소', '상어', '양', '신발', '반바지', '삽', '싱크대', '스케이트보드', '해골', '마천루', '침낭', '스마일', '달팽이', '뱀', '스노클', '눈송이', '눈사람', '축구공', '양말', '스피드보트', '거미', '숟가락', '스프레드시트', '정사각형', '다람쥐', '계단', '별', '스테이크', '스테레오', '청진기', '바늘', '정지 신호', '난로', '딸기', '가로등', '잠수함', '여행 가방', '태양', '백조', '스웨터', '그네', '칼', '주사기', '티셔츠', '테이블', '찻주전자', '곰인형', '전화기', '텔레비전', '테니스 라켓', '텐트', '호랑이', '토스터', '발가락', '화장실', '치아', '칫솔', '치약', '토네이도', '트랙터', '신호등', '기차', '나무', '삼각형', '트롬본', '트럭', '트럼펫', '우산', '속옷', '승합차', '꽃병', '바이올린', '세탁기', '수박', '워터슬라이드', '고래', '바퀴', '풍차', '와인 병', '와인 잔', '손목시계', '요가', '얼룩말', '지그재그']

class SELayer(nn.Module):
    def __init__(self, channel, reduction=16):
        super(SELayer, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channel, channel // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channel // reduction, channel, bias=False),
            nn.Sigmoid()
        )

    def forward(self, x):
        b, c, _, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1, 1)
        return x * y.expand_as(x)


def conv3x3(in_planes, out_planes, stride=1):
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)


class SEBottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, groups=1,
                 base_width=64, dilation=1, norm_layer=None,
                 *, reduction=16):
        super(SEBottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride,
                               padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4)
        self.relu = nn.ReLU(inplace=True)
        self.se = SELayer(planes * 4, reduction)

        self.stride = stride

        self.shortcut = nn.Sequential()
        if stride != 1 or inplanes != planes * self.expansion:
            self.shortcut = nn.Sequential(
                nn.Conv2d(inplanes, planes * self.expansion, stride = stride, kernel_size = 1, bias = False),
                nn.BatchNorm2d(planes * self.expansion)
            )

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)
        out = self.se(out)

        out += self.shortcut(x)
        out = self.relu(out)

        return out

class ResNet(nn.Module):
    def __init__(self, block, num_block, num_classes=345):
        super().__init__()

        self.in_channels = 64

        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 64, kernel_size = 7, stride = 2, padding = 3, bias = False),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size = 3, stride = 2, padding = 1)
        )

        self.conv2_x = self._make_layer(block, 64, num_block[0], 1)
        self.conv3_x = self._make_layer(block, 128, num_block[1], 2)
        self.conv4_x = self._make_layer(block, 256, num_block[2], 2)
        self.conv5_x = self._make_layer(block, 512, num_block[3], 2)

        self.avg_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, 345)

    def _make_layer(self, block, out_channels, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_channels, out_channels, stride))
            self.in_channels = out_channels * block.expansion

        return nn.Sequential(*layers)

    def forward(self, x):
        output = self.conv1(x)
        output = self.conv2_x(output)
        x = self.conv3_x(output)
        x = self.conv4_x(x)
        x = self.conv5_x(x)
        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

def se_resnet152(num_classes=328):
    model = ResNet(SEBottleneck, [3, 8, 36, 3], num_classes=num_classes)
    model.avgpool = nn.AdaptiveAvgPool2d(1)
    return model

def get_label(indices):
    final_label = []
    ko_final_label = []
    for index in indices:
        final_label.append(label[index])
        ko_final_label.append(koLabel[index])
    return final_label, ko_final_label

# 모델을 로드하는 함수
def load_model():
    model = se_resnet152()  # 학습한 모델 클래스를 여기에 넣어야 합니다
    model.load_state_dict(torch.load('senet_final.pth', map_location=torch.device('cpu'), weights_only=True))
    model.eval()  # 모델을 평가 모드로 전환
    return model

# 이미지를 예측하는 함수
def predict(image, model):
    # 모델로 예측 수행
    with torch.no_grad():
        output = model(torch.from_numpy(image).float())  # 모델에 이미지를 입력하여 예측 수행
        # _, predicted = torch.max(output, 1)  # 가장 높은 확률을 가진 클래스 선택
        softmaxprob = F.softmax(output, dim=1)
        value, top5_indices = torch.topk(softmaxprob, 5, dim=1)
        eng_label, kor_label = get_label(top5_indices[0].tolist())
        # top5_prob = value.tolist()
    
    return value.tolist(), eng_label, kor_label#label[predicted.item()]  # 예측한 클래스 반환