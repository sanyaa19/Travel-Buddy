import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone

def slugify(name, code):
    return f"{name.strip().replace(' ', '-')}-{code.strip().upper()}"

def build_url(src_name, src_code, dst_name, dst_code, date=None):
    src_slug = slugify(src_name, src_code)
    dst_slug = slugify(dst_name, dst_code)
    url = f"https://etrain.info/trains/{src_slug}-to-{dst_slug}"
    if date:
        url += f"?date={date}"
    return url

def get_booking_classes(row):
    classes = []
    booking_div = row.find('div', class_='flexRow')
    if booking_div:
        for link in booking_div.find_all('a', class_='cavlink'):
            classes.append(link.text.strip())
    return classes

def get_train_info(row):
    try:
        train_data = json.loads(row['data-train'])
        booking_available = row.get('book', '0') == '1'
        advance_reservation_period = row.get('ar', '0')
        start_date = row.get('sd', '')
        end_date = row.get('ed', '')
        booking_classes = get_booking_classes(row)
        notices = []

        for icon in row.find_all('i', class_='icon-info-circled'):
            if 'etitle' in icon.attrs:
                notice = re.sub(r'<[^>]+>', '', icon['etitle']).replace('&quot;', '"')
                notices.append(notice)

        has_pantry = bool(row.find('i', class_='icon-food'))
        limited_run = bool(row.find('i', class_='icon-date'))

        return {
            'train_number': train_data.get('num', ''),
            'train_name': train_data.get('name', ''),
            'train_type': train_data.get('typ', ''),
            'source': train_data.get('s', ''),
            'departure_time': train_data.get('st', ''),
            'destination': train_data.get('d', ''),
            'arrival_time': train_data.get('dt', ''),
            'duration': train_data.get('tt', ''),
            'booking_available': booking_available,
            'advance_reservation_period': advance_reservation_period,
            'start_date': start_date,
            'end_date': end_date,
            'booking_classes': booking_classes,
            'notices': notices,
            'has_pantry': has_pantry,
            'is_limited_run': limited_run
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing row: {e}")
        return None

def has_non_local_trains(trains):
    keywords = ['express', 'rajdhani', 'shatabdi', 'duronto', 'garib rath', 'superfast', 'super fast', 'fast', 'mail', 'special']
    return any(any(k in train['train_name'].lower() or k in train['train_type'].lower() for k in keywords) for train in trains)

def has_local_trains(trains):
    keywords = ['local', 'suburban', 'passenger', 'memu', 'dmu', 'emu']
    return any(any(k in train['train_name'].lower() or k in train['train_type'].lower() for k in keywords) for train in trains)

def get_trains_by_logic(trains, local_tz):
    current_time = datetime.now(local_tz)
    print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

    for train in trains:
        try:
            if train['departure_time']:
                h, m = map(int, train['departure_time'].split(':'))
                departure_naive = current_time.replace(hour=h, minute=m, second=0, microsecond=0)
                departure_dt = local_tz.localize(departure_naive)

                if departure_dt < current_time:
                    departure_dt += timedelta(days=1)

                train['departure_datetime'] = departure_dt
                train['departure_datetime_str'] = departure_dt.strftime('%Y-%m-%d %H:%M')
            else:
                raise ValueError("No departure time")
        except Exception as e:
            print(f"Error parsing departure time for train {train.get('train_number')}: {e}")
            train['departure_datetime'] = current_time + timedelta(days=365)
            train['departure_datetime_str'] = 'Unknown'

    sorted_trains = sorted(trains, key=lambda x: x['departure_datetime'])

    if has_non_local_trains(sorted_trains) and has_local_trains(sorted_trains):
        print("🚄 Both local and non-local trains detected! Showing first 3 trains.")
        return sorted_trains[:3], "mixed"
    elif has_non_local_trains(sorted_trains):
        non_locals = [t for t in sorted_trains if any(k in t['train_name'].lower() or k in t['train_type'].lower()
                                                      for k in ['express', 'rajdhani', 'shatabdi', 'duronto', 'garib rath', 'superfast', 'super fast', 'fast', 'mail', 'special'])]
        print("🚄 Only non-local trains detected! Showing next 3 non-local trains.")
        return non_locals[:3], "non_local"
    elif has_local_trains(sorted_trains):
        end_time = current_time + timedelta(hours=1)
        locals_in_1hr = [t for t in sorted_trains if t['departure_datetime'] <= end_time]
        if locals_in_1hr:
            print("🔍 Only local trains detected! Showing those within 1 hour.")
            return locals_in_1hr, "local"
        else:
            print("⚠️ No local trains within 1 hour. Showing next 3 trains.")
            return sorted_trains[:3], "local_fallback"
    else:
        print("🚂 No specific types found. Showing next 3 trains.")
        return sorted_trains[:3], "other"

def scrape_trains_between(src_name, src_code, dst_name, dst_code, output_json=None):
    local_tz = get_localzone()
    current_date = datetime.now(local_tz).strftime("%Y%m%d")

    url = build_url(src_name, src_code, dst_name, dst_code, current_date)
    print(f"\nFetching trains from {src_name} ({src_code}) to {dst_name} ({dst_code})")
    print(f"Date: {current_date}")
    print(f"URL: {url}\n")

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'text/html',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch page: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    if soup.find('div', class_='warn'):
        warn_text = soup.find('div', class_='warn').get_text(strip=True)
        print(f"❗ Error: {warn_text}")
        print("Please check the station codes you entered. They might be incorrect.")
        return None

    train_rows = soup.find_all('tr', attrs={'data-train': True})

    if not train_rows:
        print("⚠️ No train data found between the provided stations.")
        return None

    trains = [get_train_info(row) for row in train_rows if get_train_info(row)]
    print(f"\nTotal trains found: {len(trains)}")

    selected_trains, train_type = get_trains_by_logic(trains, local_tz)

    for train in selected_trains:
        if isinstance(train.get('departure_datetime'), datetime):
            train['departure_datetime'] = train['departure_datetime'].strftime('%Y-%m-%d %H:%M:%S')

    print(f"\nSelected trains: {len(selected_trains)}")

    print(f"\n{'='*80}")
    if train_type == "mixed":
        print("FIRST 3 TRAINS (Mixed Local and Non-Local)")
    elif train_type == "non_local":
        print("NEXT 3 NON-LOCAL TRAINS")
    elif train_type == "local":
        print("ALL LOCAL TRAINS UP TO 1 HOUR")
    elif train_type == "local_fallback":
        print("FALLBACK: NEXT 3 TRAINS (NO LOCAL TRAINS WITHIN 1 HOUR)")
    else:
        print("NEXT 3 TRAINS (GENERAL)")
    print(f"{'='*80}")

    for i, train in enumerate(selected_trains, 1):
        print(f"\n{i}. Train No: {train['train_number']}")
        print(f"   Name: {train['train_name']}")
        print(f"   Type: {train['train_type']}")
        print(f"   Departure: {train['departure_time']} from {train['source']}")
        print(f"   Arrival: {train['arrival_time']} at {train['destination']}")
        print(f"   Duration: {train['duration']}")
        print(f"   Booking Classes: {', '.join(train['booking_classes']) if train['booking_classes'] else 'None'}")
        print("-" * 60)

    if output_json and selected_trains:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(selected_trains, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Saved train data to {output_json}")

    return selected_trains

def get_station_input():
    print("Indian Railways Train Search Tool")
    print("="*50)
    src_name = input("Enter source station name (e.g., Howrah Jn): ").strip()
    src_code = input("Enter source station code (e.g., HWH): ").strip().upper()
    dst_name = input("Enter destination station name (e.g., Chittaranjan): ").strip()
    dst_code = input("Enter destination station code (e.g., CRJ): ").strip().upper()
    return src_name, src_code, dst_name, dst_code

def main():
    try:
        src_name, src_code, dst_name, dst_code = get_station_input()
        output_json = "next_3_trains.json"
        trains = scrape_trains_between(src_name, src_code, dst_name, dst_code, output_json)
        if trains:
            print(f"\n✅ Successfully found {len(trains)} trains.")
        else:
            print(f"\n❌ No trains found.")
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    main()
