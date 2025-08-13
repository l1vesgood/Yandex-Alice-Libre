from flask import Flask, request
import logging, json, requests
from datetime import datetime
import pytz
import hashlib

app = Flask(__name__)

logging.basicConfig(level=logging.INFO) #* Поменять на DEBUG при тестировании
logger = logging.getLogger(__name__)

username = "your libre link up email"               #! ВСТАВЬТЕ СВОИ ДАННЫЕ
password = "your libre link up password"
port = 5000                                         # ПОРТ
max_range = 10                                      # Предупреждение
min_range = 3.9

url = "https://api.libreview.ru"                    # API в России
version = "4.7.0"
headers = {
    "product": "llu.android",
    "version": version,
    "accept-encoding": "gzip",
    "cache-control": "no-cache",
    "connection": "Keep-Alive",
    "content-type": "application/json"
}

# Настройка логов
info_handler = logging.FileHandler("logs.log", encoding="utf-8")
info_handler.setLevel(logging.INFO)
logger.addHandler(info_handler)

# Login and acquire JWT token
libre_response = requests.post(
    f"{url}/llu/auth/login",
    headers=headers,
    json={"email": username, "password": password},
)
libre_data = libre_response.json()
jwt_token = libre_data["data"]["authTicket"]["token"]
headers["Authorization"] = f"Bearer {jwt_token}"

#? account id в headers
account_id = libre_data["data"]["user"]["id"]
account_id_hash = hashlib.sha256(account_id.encode()).hexdigest()
headers["account-id"] = account_id_hash

@app.route("/", methods=["POST"])
def main():
    logger.debug(request.json)

    response = {
        "version": request.json["version"],
        "session": request.json["session"],
        "response": {
            "end_session": True # Завершить сессию(быстрый выход)
        }
    }

    req = request.json
    if req["session"]["new"]:
        libre_request = requests.get(f"{url}/llu/connections", headers=headers)
        connections = libre_request.json()
        logger.debug(connections["data"][0]["glucoseMeasurement"])

        curret = connections["data"][0]["glucoseMeasurement"]["Value"]
        arrow = connections["data"][0]["glucoseMeasurement"]["TrendArrow"]

        arrow_text = "ошибка"
        status = ""
        
        if arrow == 3: #? Можно сделать match
            arrow_text = "стабильная"
        elif arrow == 4:
            arrow_text = "диагональная вверх"
        elif arrow == 5:
            arrow_text = "вверх"
        elif arrow == 2:
            arrow_text = "диагональная вниз"
        elif arrow == 1:
            arrow_text = "вниз"

        
        if curret >= max_range:
            status = "Осторожно, высокий уровень глюкозы, "
        elif curret <= min_range:
            status = "Осторожно, низкий уровень глюкозы, "
            

        measurement_time = datetime.strptime(connections["data"][0]["glucoseMeasurement"]["Timestamp"], "%m/%d/%Y %I:%M:%S %p")
        local_tz = pytz.timezone('Europe/Moscow') 
        measurement_time = local_tz.localize(measurement_time)
        now = datetime.now(local_tz)
        minutes_ago = (now - measurement_time).total_seconds() // 60

        at = measurement_time.strftime('%H:%M')
        ago = f"{int(minutes_ago)} минут назад" if minutes_ago < 60 else f"{int(minutes_ago // 60)} часов {int(minutes_ago % 60)} минут назад"

        rs = f"{status}Текущий уровень глюкозы {curret}, был отсканирован в {at}, это {ago}, стрелка {arrow_text}"
        response["response"]["text"] = rs
        
    else:
        pass

    return json.dumps(response)

if __name__ == '__main__':
    app.run(port=port, ssl_context='adhoc', host="0.0.0.0")

