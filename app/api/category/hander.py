import torch
import torch.nn.functional as F

import torch
import torch.nn.functional as F

async def predict_category_handler(
    text: str,
    model,
    tokenizer,
    config
):
    id_to_intent = config.id2label

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    inputs = tokenizer(
        text,
        max_length=512,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )

    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)

    with torch.no_grad():
        logits = model(input_ids=input_ids, attention_mask=attention_mask).logits

    probabilities = F.softmax(logits, dim=1)[0]
    predicted_label_idx = torch.argmax(probabilities).item()

    label_probabilities = [
        {
            "id": idx,
            "label": id_to_intent.get(idx, "Unknown"),
            "probability": round(prob.item(), 6)
        }
        for idx, prob in enumerate(probabilities)
    ]

    label_probabilities.sort(key=lambda x: x["probability"], reverse=True)

    predicted_category = next(
        (item for item in label_probabilities if item["id"] == predicted_label_idx),
        {"id": predicted_label_idx, "label": "Unknown", "probability": 0.0}
    )

    return label_probabilities, predicted_category
