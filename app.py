from flask import Flask, render_template, request, jsonify
import pandas as pd
import random
import io

app = Flask(__name__)

participants = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_data', methods=['POST'])
def load_data():
    global participants
    data = request.get_json()
    pasted_text = data.get('data', '')

    if not pasted_text:
        return jsonify({'error': '沒有提供資料'}), 400

    participants = []
    participant_count = 0
    total_chances = 0
    lines = pasted_text.strip().split('\n')

    name_col_index = -1
    count_col_index = -1

    for i, line in enumerate(lines):
        line = line.strip()
        if not line: # 跳過空行
            continue

        columns = line.split('\t') # 假設用 Tab 分隔

        # 嘗試自動檢測標題行 (如果第一行包含"名字"和"抽獎次數")
        if i == 0:
            try:
                name_col_index = columns.index('名字')
                count_col_index = columns.index('抽獎次數')
                continue # 跳過標題行
            except ValueError:
                # 沒有找到標題，假設第一列是名字，第二列是次數
                if len(columns) >= 2:
                    name_col_index = 0
                    count_col_index = 1
                else:
                    return jsonify({'error': '無法確定 "名字" 和 "抽獎次數" 的欄位。請確保資料至少有兩欄，且以 Tab 分隔。'}), 400

        if name_col_index == -1 or count_col_index == -1:
             return jsonify({'error': '內部錯誤：無法確定欄位索引'}), 500 # 理論上不應發生

        if len(columns) > max(name_col_index, count_col_index):
            name = columns[name_col_index].strip()
            count_str = columns[count_col_index].strip()

            if not name: # 跳過名字為空的行
                continue

            try:
                count = int(float(count_str)) # 允許小數，但轉換為整數
                if count > 0:
                    participants.extend([name] * count)
                    participant_count += 1
                    total_chances += count
            except (ValueError, TypeError):
                # 如果轉換失敗，可以選擇忽略該行或報錯
                # return jsonify({'error': f'第 {i+1} 行的抽獎次數 "{count_str}" 無法識別為數字。'}), 400
                print(f'警告：忽略第 {i+1} 行，抽獎次數 "{count_str}" 無法識別為數字。')
                continue # 選擇忽略該行
        else:
            # 如果欄位數不足，可以選擇忽略該行或報錯
            # return jsonify({'error': f'第 {i+1} 行的資料格式不正確。'}), 400
             print(f'警告：忽略第 {i+1} 行，欄位數量不足。')
             continue # 選擇忽略該行

    if not participants:
        return jsonify({'error': '處理後的資料為空，請檢查貼上的內容格式是否正確。'}), 400

    return jsonify({'message': f'成功載入 {participant_count} 位參與者的資料，總共 {total_chances} 個抽獎機會。'}), 200

@app.route('/draw', methods=['POST'])
def draw_winners():
    global participants
    data = request.get_json()
    num_winners = data.get('num_winners', 1)

    if not participants:
        return jsonify({'error': '請先載入參與者名單'}), 400

    unique_participants = list(set(participants))

    if num_winners > len(unique_participants):
        return jsonify({'error': f'抽獎人數 ({num_winners}) 不能超過實際參與者數量 ({len(unique_participants)})'}), 400

    if num_winners > 2:
        return jsonify({'error': '每次最多只能抽出 2 位得獎者'}), 400

    if len(participants) < num_winners:
         return jsonify({'error': f'剩餘抽獎機會 ({len(participants)}) 不足 {num_winners} 位'}), 400

    # 先準備一份用於動畫的名單 (打亂順序增加隨機感)
    animation_names = list(unique_participants) # 複製一份不重複名單
    random.shuffle(animation_names)

    # 執行抽獎邏輯
    winners = []
    # 我們需要從 unique_participants 中抽獎，以確保一次抽獎內不重複
    if len(unique_participants) >= num_winners:
        winners = random.sample(unique_participants, num_winners)
        # 從 participants 列表中移除已抽中的得獎者 (根據抽獎次數移除)
        for winner in winners:
            # 只移除一次該得獎者的機會
            if winner in participants:
                participants.remove(winner)
    else:
         # 這種情況理論上已經在前面被攔截，但為了保險起見
         return jsonify({'error': '可用獨立參與者數量不足，無法抽出不重複的得獎者'}), 400

    return jsonify({
        'winners': winners,
        'remaining_participants_count': len(participants),
        'animation_names': animation_names # 將用於動畫的名單返回給前端
    })

if __name__ == '__main__':
    # app.run(debug=True, port=5001) # 開發模式
    app.run() # 生產模式下由 Gunicorn 等伺服器管理，這行其實不會被 Gunicorn 執行，但保留無害
    
