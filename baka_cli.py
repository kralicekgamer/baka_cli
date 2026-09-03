import requests
import json
import argparse
import sys
import getpass
import keyring
from datetime import datetime

def get_token(username, password, base):
    url = f"{base.rstrip('/')}/api/login"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = f"client_id=ANDR&grant_type=password&username={username}&password={password}"
    return requests.post(url, data=payload, headers=headers).json()['access_token']

def get_timetable(token, base):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(
        f"{base.rstrip('/')}/api/3/timetable/actual",
        headers=headers,
    ).json()


def build_lookup(items, key="Id"):
    return {item[key]: item for item in items}


DAY_COL  = 9
CELL     = 8
RST      = "\033[0m"

DAY_NAMES = {1: "Po", 2: "Út", 3: "St", 4: "Čt", 5: "Pá", 6: "So", 7: "Ne"}


def render_cell(text, width, fg="", bg=""):
    t = str(text)[:width].center(width)
    color = bg + fg
    return " " + (color + t + RST if color else t) + " "

def hline(lft, mid, rgt, fill, nh):
    return lft + fill * (DAY_COL + 2) + mid + mid.join([fill * (CELL + 2)] * nh) + rgt


def get_atom_data(atom, subjects_lk, teachers_lk, rooms_lk):
    if atom is None:
        return ("", "", "")

    change = atom.get("Change")
    if change:
        ct = change.get("ChangeType", "")

        if ct == "Removed":
            return ("─" * (CELL - 2), "", "")

        if ct == "Absence":
            abbrev = change.get("TypeAbbrev") or "ABN"
            return (abbrev, "", "")

        subj      = subjects_lk.get(atom.get("SubjectId"), {})
        subj_abbrev = subj.get("Abbrev") or "SUP"
        teacher_id  = atom.get("TeacherId")
        t_abbrev    = teachers_lk.get(teacher_id, {}).get("Abbrev", "") if teacher_id else ""
        room_id = change.get("RoomId") or atom.get("RoomId")
        room_abbrev = rooms_lk.get(room_id, {}).get("Abbrev", "") if room_id else ""
        return (subj_abbrev, t_abbrev, room_abbrev)

    subj = subjects_lk.get(atom.get("SubjectId"), {})
    tchr = teachers_lk.get(atom.get("TeacherId"), {})
    room = rooms_lk.get(atom.get("RoomId"), {})
    return (subj.get("Abbrev") or "", tchr.get("Abbrev") or "", room.get("Abbrev") or "")


def get_fg(atom, line_idx):
    if atom is None:
        return ""
    change = atom.get("Change")
    if change and change.get("ChangeType") == "Absence":
        return "\033[1;33m" if line_idx == 0 else ""
    return ["\033[1;97m", "\033[94m", "\033[92m"][line_idx]


def get_bg(atom, day_date, hour):
    if atom is None:
        return ""

    change = atom.get("Change")
    if change and change.get("ChangeType") == "Removed":
        return "\033[42m"

    now = datetime.now()
    if day_date == now.date():
        try:
            begin = datetime.strptime(hour.get("BeginTime", ""), "%H:%M").time()
            end = datetime.strptime(hour.get("EndTime", ""), "%H:%M").time()
        except ValueError:
            begin = end = None
        if begin is not None and begin <= now.time() < end:
            return "\033[41m"

    if change:
        return "\033[43m"
    return ""


def make_row(day_text, day_fg, cell_parts):
    S = "│"
    return S + render_cell(day_text, DAY_COL, day_fg) + S + S.join(cell_parts) + S


def print_timetable(data):
    hours_lk    = build_lookup(data["Hours"])
    subjects_lk = build_lookup(data["Subjects"])
    teachers_lk = build_lookup(data["Teachers"])
    rooms_lk    = build_lookup(data["Rooms"])

    days = [d for d in data["Days"] if d.get("DayType") != "Undefined"]

    seen, hour_ids = set(), []
    for day in days:
        for atom in day.get("Atoms", []):
            if atom["HourId"] not in seen:
                seen.add(atom["HourId"])
                hour_ids.append(atom["HourId"])
    hour_ids.sort(key=lambda h: hours_lk.get(h, {}).get("Start", 0))

    grid = {}
    for di, day in enumerate(days):
        grid[di] = {atom["HourId"]: atom for atom in day.get("Atoms", [])}

    nh = len(hour_ids)

    print()
    print(hline("┌", "┬", "┐", "─", nh))

    cap_cells = [render_cell(hours_lk.get(h, {}).get("Caption", "?") + ".", CELL, "\033[36m")  for h in hour_ids]
    beg_cells = [render_cell(hours_lk.get(h, {}).get("BeginTime", ""),       CELL, "\033[90m") for h in hour_ids]
    end_cells = [render_cell(hours_lk.get(h, {}).get("EndTime", ""),         CELL, "\033[90m") for h in hour_ids]

    print(make_row("", "", cap_cells))
    print(make_row("", "", beg_cells))
    print(make_row("", "", end_cells))

    for di, day in enumerate(days):
        day_name = DAY_NAMES.get(day["DayOfWeek"], "?")
        date_str = datetime.fromisoformat(day["Date"]).strftime("%d.%m.")
        day_date = datetime.fromisoformat(day["Date"]).date()

        atoms     = [grid[di].get(hid) for hid in hour_ids]
        atom_data = [get_atom_data(a, subjects_lk, teachers_lk, rooms_lk) for a in atoms]

        rows = [[], [], []]
        for atom, hour_id, lines in zip(atoms, hour_ids, atom_data):
            bg = get_bg(atom, day_date, hours_lk.get(hour_id, {}))
            for li in range(3):
                rows[li].append(render_cell(lines[li], CELL, get_fg(atom, li), bg))

        print(hline("├", "┼", "┤", "─", nh))
        print(make_row(day_name, "\033[1;97m", rows[0]))
        print(make_row(date_str, "\033[90m",   rows[1]))
        print(make_row("",       "",            rows[2]))

    print(hline("└", "┴", "┘", "─", nh))
    print()



def login():
    try:
        base = keyring.get_password("baka-cli", "base")
        username = keyring.get_password("baka-cli", "username")
        password = keyring.get_password("baka-cli", "password")
    except Exception:
        base = None
        username = None
        password = None

    if not base or not username or not password:
        username = input("Zadej zde svoje uživatelské jméno: ")
        password = getpass.getpass("Zadej zde svoje heslo: ")
        base = input(
            "Zadej zde svojí URL (https://marvdf.bakalari.cz:444): "
        ).strip() or "https://marvdf.bakalari.cz:444"
        token = get_token(username, password, base)
        keyring.set_password("baka-cli", "base", base)
        keyring.set_password("baka-cli", "username", username)
        keyring.set_password("baka-cli", "password", password)
        return token, base

    return get_token(username, password, base), base


token, base = login()

print_timetable(get_timetable(token, base))
