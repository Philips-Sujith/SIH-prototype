"""
alert_templates.py - Fixed, reviewed static multilingual alert templates
for ClimateGuard India real-time public health warnings.

Languages: English, Tamil (தமிழ்), Hindi (हिन्दी)
Tiers: Caution, Danger, Extreme Danger / Extreme, Severe, Low
"""

import html
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("climateguard.alerts")

# FIXED, PRE-REVIEWED TEMPLATES PER RISK TIER (DO NOT LLM-GENERATE)
ALERT_TEMPLATES = {
    "Caution": {
        "en": (
            "⚠️ Heat Advisory — {district}: Elevated warmth expected {time_window} today (WBGT {wbgt}°C). "
            "Limit strenuous outdoor labor between {peak_start}–{peak_end}. "
            "Children and the elderly should rest in shaded areas. Drink water frequently throughout the day."
        ),
        "ta": (
            "⚠️ வெப்ப ஆலோசனை — {district}: இன்று {time_window} வரை மிதமான வெப்பம் எதிர்பார்க்கப்படுகிறது (WBGT {wbgt}°C). "
            "{peak_start} முதல் {peak_end} வரை கடினமான வெளிப்புற வேலைகளைக் குறைக்கவும். "
            "குழந்தைகள் மற்றும் முதியோர் நிழலில் ஓய்வெடுக்கவும். அடிக்கடி தண்ணீர் குடிக்கவும்."
        ),
        "hi": (
            "⚠️ गर्मी सलाह — {district}: आज {time_window} तक हल्की गर्मी की संभावना है (WBGT {wbgt}°C)। "
            "{peak_start} से {peak_end} के बीच भारी धूप में काम सीमित करें। "
            "बच्चे और बुज़ुर्ग छायादार स्थानों पर रहें। बार-बार पानी पीते रहें।"
        )
    },
    "Danger": {
        "en": (
            "⚠️ Heat Alert — {district}: Extreme heat expected {time_window} today (WBGT {wbgt}°C). "
            "Avoid outdoor work between {peak_start}–{peak_end}. "
            "Pregnant women and elderly should stay indoors. Drink water every 30 minutes."
        ),
        "ta": (
            "⚠️ வெப்ப எச்சரிக்கை — {district}: இன்று {time_window} வரை கடுமையான வெப்பம் எதிர்பார்க்கப்படுகிறது (WBGT {wbgt}°C). "
            "{peak_start} முதல் {peak_end} வரை வெளியில் வேலை செய்ய வேண்டாம். "
            "கர்ப்பிணிப் பெண்கள் மற்றும் முதியோர் வீட்டிற்குள் இருக்கவும். 30 நிமிடத்திற்கு ஒருமுறை தண்ணீர் அருந்தவும்."
        ),
        "hi": (
            "⚠️ गर्मी चेतावनी — {district}: आज {time_window} तक अत्यधिक गर्मी की संभावना है (WBGT {wbgt}°C)। "
            "{peak_start} से {peak_end} तक बाहर काम करने से बचें। "
            "गर्भवती महिलाएं और बुज़ुर्ग घर के अंदर रहें। हर 30 मिनट में पानी पिएं।"
        )
    },
    "Extreme Danger": {
        "en": (
            "🚨 Extreme Heat Warning — {district}: Dangerous thermal stress expected {time_window} today (WBGT {wbgt}°C). "
            "Strictly halt all outdoor work between {peak_start}–{peak_end}. "
            "Children, pregnant women, and elderly must remain in cool indoor spaces. Drink ORS or salted lemon water every 20 minutes."
        ),
        "ta": (
            "🚨 தீவிர வெப்ப எச்சரிக்கை — {district}: இன்று {time_window} வரை மிகத் தீவிர வெப்ப அழுத்தம் எதிர்பார்க்கப்படுகிறது (WBGT {wbgt}°C). "
            "{peak_start} முதல் {peak_end} வரை வெளிப்புறப் பணிகளை முற்றிலும் நிறுத்தவும். "
            "குழந்தைகள், கர்ப்பிணிகள் மற்றும் முதியவர்கள் குளிர்ந்த அறைகளில் இருக்க வேண்டும். 20 நிமிடத்திற்கு ஒருமுறை ORS அல்லது நீர் அருந்தவும்."
        ),
        "hi": (
            "🚨 अत्यधिक गर्मी चेतावनी — {district}: आज {time_window} तक गंभीर गर्मी का प्रकोप रहेगा (WBGT {wbgt}°C)। "
            "{peak_start} से {peak_end} तक बाहर का काम पूरी तरह बंद रखें। "
            "बच्चे, गर्भवती महिलाएं और बुज़ुर्ग ठंडी जगहों पर रहें। हर 20 मिनट में ओआरएस या नींबू-पानी पिएं।"
        )
    },
    "Severe": {
        "en": (
            "🚨 Emergency Heat Red Alert — {district}: Critical life-threatening heat expected {time_window} today (WBGT {wbgt}°C). "
            "Do not go outside at all between {peak_start}–{peak_end}; emergency cooling shelters are open. "
            "Elderly, children, and patients require continuous monitoring. Drink fluids continuously and dial 108 for heat emergencies."
        ),
        "ta": (
            "🚨 அவசர வெப்ப சிவப்பு எச்சரிக்கை — {district}: இன்று {time_window} வரை உயிருக்கு ஆபத்தான வெப்பம் நிலவும் (WBGT {wbgt}°C). "
            "{peak_start} முதல் {peak_end} வரை யாரும் வெளியே செல்ல வேண்டாம்; அவசர குளிர்ச்சி மையங்கள் திறக்கப்பட்டுள்ளன. "
            "முதியோர் மற்றும் நோயாளிகளைத் தொடர்ந்து கண்காணிக்கவும். தொடர்ந்து நீர் அருந்தவும், அவசரத்திற்கு 108 ஐ அழைக்கவும்."
        ),
        "hi": (
            "🚨 आपातकालीन रेड अलर्ट — {district}: आज {time_window} तक जानलेवा गर्मी की स्थिति रहेगी (WBGT {wbgt}°C)। "
            "{peak_start} से {peak_end} तक बिल्कुल बाहर न निकलें; आपातकालीन कूलिंग शेल्टर खुले हैं। "
            "बुज़ुर्गों और बीमारों की लगातार निगरानी करें। लगातार ओआरएस और पानी पिएं, आपात स्थिति में 108 पर कॉल करें।"
        )
    },
    "Low": {
        "en": (
            "ℹ️ Heat Advisory — {district}: Normal thermal conditions expected {time_window} today (WBGT {wbgt}°C). "
            "Regular outdoor activity is permitted. Ensure standard hydration and wear light clothing."
        ),
        "ta": (
            "ℹ️ வெப்ப தகவல் — {district}: இன்று {time_window} வரை இயல்பான வெப்பம் நிலவும் (WBGT {wbgt}°C). "
            "வழக்கமான பணிகளைத் தொடரலாம். போதிய அளவு தண்ணீர் குடிக்கவும்."
        ),
        "hi": (
            "ℹ️ मौसम सूचना — {district}: आज {time_window} तक सामान्य तापमान रहेगा (WBGT {wbgt}°C)। "
            "सामान्य गतिविधियां जारी रख सकते हैं। पर्याप्त पानी पिएं।"
        )
    }
}


def normalize_category(category_raw: str) -> str:
    """Normalize risk category string to match template keys."""
    cat = (category_raw or "").strip().title()
    if cat in ["Severe", "Severe Heat"]:
        return "Severe"
    if cat in ["Extreme", "Extreme Danger", "Extremedanger"]:
        return "Extreme Danger"
    if cat in ["Danger", "High"]:
        return "Danger"
    if cat in ["Caution", "Moderate"]:
        return "Caution"
    return "Low"


def format_multilingual_alert(
    district: str,
    category: str,
    wbgt: float,
    temp: float,
    time_window: str = "11:30 AM – 4:00 PM",
    peak_start: str = "11:30 AM",
    peak_end: str = "4:00 PM"
) -> Dict[str, Any]:
    """
    Format a unified 3-language public health alert string with static reviewed templates.
    Order: English -> Tamil -> Hindi separated by horizontal dividers.
    """
    norm_cat = normalize_category(category)
    templates = ALERT_TEMPLATES.get(norm_cat, ALERT_TEMPLATES["Caution"])

    # Safe parameter dict
    params = {
        "district": district.strip(),
        "category": norm_cat,
        "time_window": time_window,
        "peak_start": peak_start,
        "peak_end": peak_end,
        "wbgt": f"{float(wbgt):.1f}",
        "temp": f"{float(temp):.1f}"
    }

    # Format each language
    en_msg = templates["en"].format(**params)
    ta_msg = templates["ta"].format(**params)
    hi_msg = templates["hi"].format(**params)

    # Combined single Telegram post with clear visual headers and dividers
    combined = (
        f"<b>[ENGLISH]</b>\n"
        f"{en_msg}\n\n"
        f"──────────────\n"
        f"<b>[தமிழ் / TAMIL]</b>\n"
        f"{ta_msg}\n\n"
        f"──────────────\n"
        f"<b>[हिन्दी / HINDI]</b>\n"
        f"{hi_msg}\n\n"
        f"<i>ClimateGuard India • Live Early Warning Telemetry</i>"
    )

    return {
        "category": norm_cat,
        "district": district,
        "wbgt": float(wbgt),
        "temp": float(temp),
        "time_window": time_window,
        "peak_start": peak_start,
        "peak_end": peak_end,
        "english": en_msg,
        "tamil": ta_msg,
        "hindi": hi_msg,
        "combined_message": combined
    }
