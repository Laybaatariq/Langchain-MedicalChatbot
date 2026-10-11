"""
Every fixed sentence of the symptom intake, in English ("en") and Roman Urdu ("ru").
Edit the wording here without touching the logic.
"""


def lang_of(language: str) -> str:
    """Router language -> text language. Urdu script falls back to English."""
    return "ru" if language == "roman_urdu" else "en"


# language code used by the emergency message helper
EMERGENCY_LANGUAGE = {"en": "english", "ru": "roman_urdu"}

INTRO = {
    "en": "I'll ask a few quick questions so I can suggest the right kind of doctor. "
          "This is not a diagnosis, and you can tap Skip on any question.",
    "ru": "Sahi qism ka doctor suggest karne ke liye kuch chhote sawal poochhe jayenge. "
          "Ye tashkhees nahi hai, aur aap kisi bhi sawal par Chhor dein dabaa sakte hain.",
}

PROGRESS = {"en": "Question {n} of {total}", "ru": "Sawal {n} / {total}"}
CONFIRM = {"en": "Done", "ru": "Theek hai"}

REASK = {
    "choice": {"en": "Please pick one of the options below, or type it.",
               "ru": "Neeche diye gaye options mein se ek chunein, ya likh dein."},
    "multi_choice": {"en": "Please tap the options that apply, then Done, or type them separated by commas.",
                     "ru": "Jo options lagu hon unhein chunein aur Theek hai dabayen, ya comma laga kar likh dein."},
    "scale": {"en": "Please give a number from 1 to 10.", "ru": "1 se 10 ke beech ka number batayein."},
    "age": {"en": "Please pick an age group or type the age in years.",
            "ru": "Umar ka group chunein ya saalon mein likh dein."},
    "text": {"en": "Please type your answer, or tap Skip.", "ru": "Apna jawab likh dein, ya Chhor dein dabayen."},
}

CANCELLED = {
    "en": "Okay, I've stopped the questions. You can ask me anything else, or describe your symptoms again at any time.",
    "ru": "Theek hai, sawal rok diye gaye hain. Aap kuch aur poochh sakte hain, ya kabhi bhi dobara apni takleef bata sakte hain.",
}

# words that stop the intake (compared in lower case)
CANCEL_WORDS = {
    "cancel", "stop", "exit", "quit", "never mind", "nevermind", "forget it",
    "ruk jao", "rukjao", "band karo", "rehne do", "rehnay do", "cancel karo",
}

OUTCOME = {
    "urgent": {
        "en": "Based on your answers, it would be best to see a doctor soon, ideally today or within a day.",
        "ru": "Aap ke jawabat ke mutabiq behtar hai ke jaldi doctor se milein, aaj ya ek din ke andar.",
    },
    "routine": {
        "en": "Based on your answers, booking an appointment in the next few days is a good idea.",
        "ru": "Aap ke jawabat ke mutabiq agle chand dinon mein appointment lena munasib hoga.",
    },
    "self_care": {
        "en": "Your answers suggest this is mild. General self-care is usually enough, "
              "but see a doctor if it lasts or gets worse.",
        "ru": "Aap ke jawabat se lagta hai ke takleef halki hai. Aam dekh-bhaal aksar kaafi hoti hai, "
              "lekin agar ye barhe ya lambi chale to doctor se milein.",
    },
}

URGENCY_LABEL = {
    "urgent": {"en": "See a doctor soon", "ru": "Jaldi doctor se milein"},
    "routine": {"en": "Book an appointment", "ru": "Appointment lein"},
    "self_care": {"en": "Self-care", "ru": "Ghar par dekh-bhaal"},
}

REASONS = {
    "severe": {"en": "severe symptoms ({n}/10)", "ru": "takleef bohat shadeed hai ({n}/10)"},
    "moderate": {"en": "moderately strong symptoms ({n}/10)", "ru": "takleef kaafi zyada hai ({n}/10)"},
    "worsening": {"en": "the symptoms are getting worse", "ru": "takleef barh rahi hai"},
    "long": {"en": "the symptoms have lasted several days", "ru": "takleef kai din se hai"},
    "long_fever": {"en": "fever together with symptoms lasting several days",
                   "ru": "bukhar ke saath takleef kai din se hai"},
    "fever_vulnerable": {"en": "fever in a very young child or an older adult",
                         "ru": "bohat chhote bachay ya buzurg mein bukhar"},
    "infant": {"en": "the patient is under 1 year old", "ru": "mareez ki umar 1 saal se kam hai"},
    "urgent_phrase": {"en": "you mentioned: {label}", "ru": "aap ne zikr kiya: {label}"},
}

FIELDS = {
    "problem": {"en": "Problem", "ru": "Takleef"},
    "duration": {"en": "How long", "ru": "Kitne waqt se"},
    "severity": {"en": "Severity", "ru": "Shiddat"},
    "trend": {"en": "Trend", "ru": "Halat"},
    "associated": {"en": "Other symptoms", "ru": "Saath mein"},
    "age": {"en": "Age", "ru": "Umar"},
}

HEADINGS = {
    "summary": {"en": "What you told me", "ru": "Aap ne bataya"},
    "why": {"en": "Why this advice", "ru": "Ye mashwara kyun"},
    "doctor_type": {"en": "Suggested doctor type", "ru": "Suggest kiya gaya doctor"},
}

FALLBACK_NOTE = {
    "en": "No sample {name} is listed, so these are General Physicians.",
    "ru": "Is waqt {name} maujood nahi, is liye General Physician dikhaye ja rahe hain.",
}

FOOTER = {
    "en": "This is guidance, not a diagnosis. If your symptoms suddenly get worse, go to emergency care.",
    "ru": "Ye rehnumai hai, tashkhees nahi. Agar takleef achanak barh jaye to foran emergency mein jayein.",
}