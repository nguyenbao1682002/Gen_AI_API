import json
from thefuzz import fuzz

def querytag_function(input_data):
    """
    Function to query tags from DynamoDB based on inputText.
    """
    threshold = 50
    with open('./data/Column Descriptions.json', 'r', encoding='utf-8') as f:
        kb = json.load(f)
    print("Knowledge base loaded with", len(kb), "items.")
    print("Input data received:", input_data.get('inputText'))
    inputText = input_data.get('inputText', '')
    input_text = inputText.lower()
    matched = []

    for item in kb:
        desc_vn = item['description-vn'].lower()
        score = fuzz.token_set_ratio(input_text, desc_vn)
        if score >= threshold:
            matched.append({
                "tag": item['tag'],
                "description": item['description-vn'],
                "score": score
            })
    
    matched.sort(key=lambda x: x['score'], reverse=True)

    # Giới hạn tối đa 5 tag
    top_matched = matched[:5]

    if not top_matched:
        return f"Input: {inputText}. Không tìm thấy tag nào phù hợp."

    matched_texts = []
    for item in top_matched:
        t = f"{item['tag']} ({item['description']}, Độ tương thích với câu hỏi:{item['score']})"
        matched_texts.append(t)

    matched_str = "; ".join(matched_texts)
    output = f"Input: {inputText}. Các tag tìm được: {matched_str}."
    print("Output:", output)
    return output
