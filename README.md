# Indian Railways Train Scraper

A Python tool to scrape train information from etrain.info and show the next 3 trains between two stations.

## Features

- **Interactive Input**: Enter source and destination stations with their codes
- **Next 3 Trains**: Automatically shows the next 3 trains based on departure time
- **Automatic Date/Time**: Uses current date and time automatically
- **Comprehensive Train Info**: Train number, name, type, departure/arrival times, duration, classes, etc.
- **JSON Export**: Save results to JSON file
- **Real-time Data**: Fetches live data from etrain.info

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script:
```bash
python dataset.py
```

### Example Session:
```
Indian Railways Train Search Tool
==================================================
Enter source station name (e.g., Howrah Jn): Howrah Jn
Enter source station code (e.g., HWH): HWH
Enter destination station name (e.g., Chittaranjan): Chittaranjan
Enter destination station code (e.g., CRJ): CRJ
```

## Output

The script will display:
- Total trains found between stations
- Next 3 trains based on departure time
- Detailed information for each train including:
  - Train number and name
  - Train type
  - Departure and arrival times
  - Duration
  - Running days
  - Available booking classes
  - Special features (pantry, limited run, etc.)

Results are also saved to `next_3_trains.json` for further processing.

## Station Codes

You need to provide both station name and code. Common examples:
- Howrah Jn (HWH)
- New Delhi (NDLS)
- Mumbai Central (MMCT)
- Bangalore City (SBC)
- Chennai Central (MAS)

## Notes

- The script automatically uses the current date
- Shows the next 3 trains based on departure time from source station
- Network connectivity required to fetch data from etrain.info
- Respect the website's terms of service and avoid excessive requests 