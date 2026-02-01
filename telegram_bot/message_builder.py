from datetime import date

def is_weekend(d: date):
    return d.weekday() >= 5  # Sat/Sun

def build_duty_message(target_date, shifts):
    date_str = target_date.strftime("%d %b %Y (%A)")

    if is_weekend(target_date):
        return f"📌 {date_str}\n\n🚫 Weekend, ProjectHub closed."

    if not shifts:
        return f"📌 {date_str}\n\n🚫 Public Holiday, ProjectHub closed."

    lines = [f"📌 *{date_str}*\n👥 Student Coach on Duty:\n"]
    for s in shifts:
        lines.append(f"• {s['name']} — {s['shift']} ({s['level']})")

    return "\n".join(lines)
