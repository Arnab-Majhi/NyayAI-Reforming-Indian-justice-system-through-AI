from datetime import datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
CAPACITY = 1


def conflicts(db, case, start, duration):
    end = start + timedelta(minutes=duration)
    found = []
    for other in db.all("cases"):
        if other["id"] == case["id"] or not other.get("next_hearing") or other["status"] == "Closed":
            continue
        existing = datetime.fromisoformat(other["next_hearing"])
        existing_end = existing + timedelta(minutes=other.get("hearing_duration", 60))
        if start < existing_end and end > existing:
            if other["court"] == case["court"] or other["assigned_staff"] == case["assigned_staff"]:
                found.append({"case_id": other["id"], "reference": other["reference"], "reason": "Court capacity or assigned officer overlap"})
    return found


def valid_slot(start, duration):
    local = start.astimezone(IST)
    return (start.utcoffset() is not None and local.weekday() < 5 and local.minute in (0, 30)
            and local.second == 0 and local.microsecond == 0 and local.hour >= 10
            and (local + timedelta(minutes=duration)).time() <= time(17)
            and start > datetime.now(IST))


def suggest(db, case, payload):
    options, rejected = [], []
    for day_index in range(21):
        day = payload.start_date + timedelta(days=day_index)
        if payload.deadline and day > payload.deadline:
            break
        for hour in range(10, 17):
            start = datetime.combine(day, time(hour), tzinfo=IST)
            if not valid_slot(start, payload.duration_minutes):
                continue
            overlap = conflicts(db, case, start, payload.duration_minutes)
            if overlap:
                if len(rejected) < 8:
                    rejected.append({"start": start.isoformat(), "conflicts": overlap})
            elif len(options) < 5:
                options.append({"start": start.isoformat(), "duration_minutes": payload.duration_minutes,
                                "reason": "Weekday 10:00–17:00 IST; assigned officer and court are free; within supplied deadline if any."})
        if len(options) >= 5:
            break
    return {"options": options, "conflicts": rejected, "capacity": CAPACITY,
            "rules": "Demo configuration: one matter per court/officer, weekdays 10–17 IST, 30/60 minutes. No real holiday calendar or actual judicial availability.",
            "urgency": "User-supplied deadline constrains suggestions; no legal urgency or merits ranking inferred.",
            "requires_human_confirmation": True}