import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime

SOURCE = "https://services.cinema-api.com/show/stripped/no/1/1024/?CountryAlias=no&CityAlias=OS&Channel=Web"
ITEM = "NCG968895"
VARIANTS = {"NCG968895V9", "NCG968895V12"}
LINK = "https://www.odeonkino.no/film/dune-part-three/?date={date}&attributes=IMAX"


def fetch_matches(target: date) -> list[datetime]:
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        entries = json.load(resp)["items"]

    found = []
    for entry in entries:
        if entry["mId"] != ITEM or entry["mvId"] not in VARIANTS:
            continue
        start = datetime.fromisoformat(entry["utc"].replace("Z", "+00:00")).astimezone()
        if start.date() == target:
            found.append(start)
    return sorted(found)


def notify(message: str, click_url: str) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode(),
        headers={"Title": "Available", "Priority": "urgent", "Tags": "rotating_light", "Click": click_url},
    )
    urllib.request.urlopen(req, timeout=30).close()


def alarm(seconds: int = 30) -> None:
    if sys.platform != "win32":
        return
    import winsound

    end = time.time() + seconds
    while time.time() < end:
        for freq in (880, 1320, 1760):
            winsound.Beep(freq, 200)
        time.sleep(0.3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat, default=date(2026, 12, 16))
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    print(f"Checking {args.date}")
    while True:
        try:
            found = fetch_matches(args.date)
        except Exception as e:
            if args.once:
                raise
            print(f"[{datetime.now():%H:%M:%S}] Failed: {e}")
            found = []

        if found:
            message = f"{args.date}: {', '.join(f'{s:%H:%M}' for s in found)}"
            url = LINK.format(date=args.date)
            print(f"[{datetime.now():%H:%M:%S}] Found: {message}")
            print(url)
            notify(message, url)
            alarm()
            return

        print(f"[{datetime.now():%H:%M:%S}] Nothing yet")
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
