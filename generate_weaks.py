from datetime import datetime, timedelta
def generate_weeks(year):
    weeks = []
    first_day = datetime(year, 1, 1)
    start_of_week = first_day + timedelta(days=(7 - first_day.weekday()) % 7)
    for week_number in range(1, 53):
        end_of_week = start_of_week + timedelta(days=6)
        weeks.append({
            "week_number": week_number,
            "start_date": start_of_week.strftime("%Y-%m-%d"),
            "end_date": end_of_week.strftime("%Y-%m-%d"),
            "occupied": None
        })
        start_of_week += timedelta(days=7)
        if start_of_week.year > year:
            break
    return weeks