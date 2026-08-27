def tool_predict_trend(history, sentiment):
    score = sentiment["positive"] - sentiment["negative"]

    if score > 0.2:
        trend = "likely upward"
    elif score < -0.2:
        trend = "likely downward"
    else:
        trend = "neutral / uncertain"

    return {
        "trend": trend,
        "confidence": abs(score)
    }
