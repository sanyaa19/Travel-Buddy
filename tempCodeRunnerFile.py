import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta

def slugify(name, code):
    # Converts "Howrah Jn", "HWH" -> "Howrah-Jn-HWH"
    return f"{name.strip().replace(' ', '-')}-{code.strip().upper()}"

def build_url(src_name, src_code, dst_name, dst_code, date=None):
    # Updated URL format: https://etrain.info/trains/Howrah-Jn-HWH-to-Chittaranjan-CRJ?date=20250521
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
        # Parse the data-train attribute which contains train info in JSON format
        train_data = json.loads(row['data-train'])
        
        # Get additional attributes
        booking_available = row.get('book', '0') == '1'
        advance_reservation_period = row.get('ar', '0')
        start_date = row.get('sd', '')
        end_date = row.get('ed', '')
        
        # Get booking classes
        booking_classes = get_booking_classes(row)
        
        # Get notices/remarks if any
        notices = []
        notice_icons = row.find_all('i', class_='icon-info-circled')
        for icon in notice_icons:
            if 'etitle' in icon.attrs:
                notice = icon['etitle']
                # Clean up the notice text
                notice = re.sub(r'<[^>]+>', '', notice)
                notice = notice.replace('&quot;', '"')
                notices.append(notice)
        
        # Get pantry availability
        has_pantry = bool(row.find('i', class_='icon-food'))
        
        # Get limited run info
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

def get_next_3_trains(trains):
    """Get the next 3 trains based on departure time"""
    current_time = datetime.now()
    
    # Add departure datetime to each train for sorting
    for train in trains:
        try:
            departure_time_str = train['departure_time']
            if departure_time_str:
                departure_hour, departure_minute = map(int, departure_time_str.split(':'))
                departure_dt = current_time.replace(hour=departure_hour, minute=departure_minute, second=0, microsecond=0)
                
                # If departure time is earlier than current time, it's for tomorrow
                if departure_dt < current_time:
                    departure_dt += timedelta(days=1)
                
                train['departure_datetime'] = departure_dt
                train['departure_datetime_str'] = departure_dt.strftime('%Y-%m-%d %H:%M')
            else:
                train['departure_datetime'] = current_time + timedelta(days=365)  # Far future for sorting
                train['departure_datetime_str'] = 'Unknown'
        except (ValueError, TypeError) as e:
            print(f"Error parsing departure time for train {train.get('train_number', 'Unknown')}: {e}")
            train['departure_datetime'] = current_time + timedelta(days=365)
            train['departure_datetime_str'] = 'Unknown'
    
    # Sort trains by departure time
    sorted_trains = sorted(trains, key=lambda x: x['departure_datetime'])
    
    # Convert datetime objects to strings for JSON serialization
    for train in sorted_trains[:3]:
        if 'departure_datetime' in train:
            # Convert datetime object to string
            if isinstance(train['departure_datetime'], datetime):
                train['departure_datetime'] = train['departure_datetime'].strftime('%Y-%m-%d %H:%M:%S')
    
    # Return next 3 trains
    return sorted_trains[:3]

def scrape_trains_between(src_name, src_code, dst_name, dst_code, output_json=None):
    # Get current date in YYYYMMDD format
    current_date = datetime.now().strftime("%Y%m%d")
    
    url = build_url(src_name, src_code, dst_name, dst_code, current_date)
    print(f"Fetching trains from {src_name} ({src_code}) to {dst_name} ({dst_code})")
    print(f"Date: {current_date}")
    print(f"URL: {url}")
    
    # Add headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch page: {e}")
        return None

    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find all train rows
    train_rows = soup.find_all('tr', attrs={'data-train': True})
    if not train_rows:
        print("No train data found in the page.")
        return None
    
    # Process the train data
    trains = []
    for row in train_rows:
        train_info = get_train_info(row)
        if train_info:
            trains.append(train_info)
    
    print(f"\nTotal trains found: {len(trains)}")
    
    # Get next 3 trains
    next_3_trains = get_next_3_trains(trains)
    
    print(f"Next 3 trains: {len(next_3_trains)}")
    
    # Display next 3 trains
    if next_3_trains:
        print(f"\n{'='*80}")
        print("NEXT 3 TRAINS")
        print(f"{'='*80}")
        
        for i, train in enumerate(next_3_trains, 1):
            print(f"\n{i}. Train No: {train['train_number']}")
            print(f"   Name: {train['train_name']}")
            print(f"   Type: {train['train_type']}")
            print(f"   Departure: {train['departure_time']} from {train['source']}")
            print(f"   Arrival: {train['arrival_time']} at {train['destination']}")
            print(f"   Duration: {train['duration']}")
            print(f"   Booking Classes: {', '.join(train['booking_classes']) if train['booking_classes'] else 'None'}")
            print("-" * 60)
    else:
        print(f"\nNo trains found.")
    
    if output_json and next_3_trains:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(next_3_trains, f, indent=2, ensure_ascii=False)
        print(f"\nSaved next 3 trains data to {output_json}")
    
    return next_3_trains

def get_station_input():
    """Get station information from user input"""
    print("Indian Railways Train Search Tool")
    print("="*50)
    
    # Get source station
    src_name = input("Enter source station name (e.g., Howrah Jn): ").strip()
    src_code = input("Enter source station code (e.g., HWH): ").strip().upper()
    
    # Get destination station
    dst_name = input("Enter destination station name (e.g., Chittaranjan): ").strip()
    dst_code = input("Enter destination station code (e.g., CRJ): ").strip().upper()
    
    return src_name, src_code, dst_name, dst_code

def main():
    """Main function to run the train scraper"""
    try:
        # Get user input
        src_name, src_code, dst_name, dst_code = get_station_input()
        
        # Scrape trains
        output_json = "next_3_trains.json"
        trains = scrape_trains_between(src_name, src_code, dst_name, dst_code, output_json)
        
        if trains:
            print(f"\n✅ Successfully found {len(trains)} next trains.")
            print(f"📄 Data saved to: {output_json}")
        else:
            print(f"\n❌ No trains found between the specified stations.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    main()
