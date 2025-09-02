# Here is the code to create a dynamic map from strava output.
# This code runs slowly to generate the HTML file, but it parses through both GMX files and FIT files.
# See the README for more details on how to set up and run this program!

# If you only have gmx files, there is commented out code below that only deals with gmx files and runs quickly!

# Enjoy!


import os
import glob
import numpy as np
import folium
import gzip
import pandas as pd
from fitparse import FitFile
from xml.etree import ElementTree as ET
from datetime import datetime
from argparse import ArgumentParser, Namespace



def extract_gpx_info(gpx_file: str) -> tuple:
    # extract activity name and formatted date from GPX file
    tree = ET.parse(gpx_file)
    root = tree.getroot()
    namespace = {'gpx': 'http://www.topografix.com/GPX/1/1'}

    name = root.find('.//gpx:name', namespace).text
    time = root.find('.//gpx:metadata/gpx:time', namespace).text
    date_obj = datetime.strptime(time, '%Y-%m-%dT%H:%M:%SZ')
    formatted_date = date_obj.strftime('%B %d, %Y %I:%M %p')
    return name, formatted_date

def extract_fit_info(fit_file: str, activities_df: pd.DataFrame) -> tuple:
    # extract activity name, date, and activity ID from FIT file
    try:
        fit = FitFile(fit_file)
        # Look for the 'timestamp' in the FIT file
        timestamps = [msg.get_value('timestamp') for msg in fit.get_messages('record') if msg.get_value('timestamp')]
        if not timestamps:
            return "fail", "fail", "fail"
        start_time = min(timestamps)  # take earliest timestamp
        formatted_time = start_time.strftime('%B %d, %Y %I:%M %p')
        # match to CSV to get name and ID
        match = activities_df[activities_df["Activity Date"] == formatted_time]
        if match.empty:
            return "fail", "fail", "fail"
        activity_name = match.iloc[0]["Activity Name"]
        activity_id = str(match.iloc[0]["Activity ID"])
        return activity_name, formatted_time, activity_id
    except Exception as e:
        print(f"FIT read error {fit_file}: {e}")
        return "fail", "fail", "fail"

def read_fit_trackpoints(fit_file: str) -> np.ndarray:
    """Return lat/lon points from a FIT file"""
    try:
        fit = FitFile(fit_file)
        lat_lon_data = []
        for record in fit.get_messages('record'):
            lat = record.get_value('position_lat')
            lon = record.get_value('position_long')
            if lat is not None and lon is not None:
                # convert semicircles to degrees (from google)
                lat_deg = lat * (180 / 2**31)
                lon_deg = lon * (180 / 2**31)
                lat_lon_data.append([lat_deg, lon_deg])
        return np.array(lat_lon_data)
    except:
        return np.array([])


def main(args: Namespace) -> None:
    # load activities CSV
    activities_df = pd.read_csv('activities.csv')
    activities_df["Activity Date"] = pd.to_datetime(
        activities_df["Activity Date"],
        format="%b %d, %Y, %I:%M:%S %p",
        errors="coerce"
    )
    # convert back to formatted string for matching
    activities_df["Activity Date"] = activities_df["Activity Date"].dt.strftime('%B %d, %Y %I:%M %p')

    # read GPX files
    gpx_files = glob.glob(f'{args.gpx_dir}/*.gpx')
    fit_files = glob.glob(f'{args.fit_dir}/*.fit.gz') # diff folder for fit fyi


    if not gpx_files and not fit_files:
        exit("ERROR: No GPX or FIT files found!")

    # initialize map
    map_center = [44, -71.5]  # center around NE
    m = folium.Map(location=map_center, zoom_start=6)


    # Custom tooltip CSS
    custom_css = """
    <style>
        .leaflet-tooltip.custom-tooltip-style {
            background-color: #007bff;
            color: yellow;
            border: 2px solid green;
            font-size: 16px;
            padding: 8px;
            border-radius: 3px;
        }
        .leaflet-interactive:focus {
            outline: none !important;
        }
    </style>
    """
    m.get_root().html.add_child(folium.Element(custom_css))

    #This is for processing GPX files
    for gpx_file in gpx_files:
        print(f"Reading GPX {os.path.basename(gpx_file)}")
        activity_name, activity_date = extract_gpx_info(gpx_file)
        lat_lon_data = []
        with open(gpx_file, encoding='utf-8') as file:
            for line in file:
                if '<trkpt' in line:
                    l = line.split('"')
                    lat_lon_data.append([float(l[1]), float(l[3])])
        lat_lon_data = np.array(lat_lon_data)
        if lat_lon_data.size == 0:
            continue
        lat_lon_data = lat_lon_data[::12]  # downsample

        polyline = folium.PolyLine(
            locations=lat_lon_data.tolist(),
            color="blue",
            weight=1,
            opacity=0.8,
            tooltip=f"<strong>{activity_name}</strong><br>{activity_date}<br>Click for more info"
        ).add_to(m)

        activity_id = os.path.splitext(os.path.basename(gpx_file))[0]
        strava_url = f"https://www.strava.com/activities/{activity_id}"
        popup_content = f"""
        <strong>Activity:</strong> {activity_name}<br>
        <strong>Date:</strong> {activity_date}<br>
        <a href="{strava_url}" target="_blank">View on Strava</a>
        """
        folium.Popup(popup_content, max_width=300).add_to(polyline)

    # This is for proessing FIT files
    for fit_file in fit_files:
        print(f"Reading FIT {os.path.basename(fit_file)}")
        try:
            # Decompress if needed
            if fit_file.endswith(".gz"):
                with gzip.open(fit_file, "rb") as f:
                    fit_bytes = f.read()
                fit_path = f"temp_{os.path.basename(fit_file)}"  # temp name
                with open(fit_path, "wb") as temp_file:
                    temp_file.write(fit_bytes)
            else:
                fit_path = fit_file

            activity_name, activity_date, activity_id = extract_fit_info(fit_path, activities_df)
            if activity_name == "fail":
                print(f"Failed to match {fit_file}")
                continue

            lat_lon_data = read_fit_trackpoints(fit_path)
            if lat_lon_data.size == 0:
                print(f"No trackpoints in {fit_file}")
                continue
            lat_lon_data = lat_lon_data[::8]

            polyline = folium.PolyLine(
                locations=lat_lon_data.tolist(),
                color="blue",
                weight=1,
                opacity=0.8,
                tooltip=f"<strong>{activity_name}</strong><br>{activity_date}<br>Click for more info"
            ).add_to(m)

            strava_url = f"https://www.strava.com/activities/{activity_id}"
            popup_content = f"""
            <strong>Activity:</strong> {activity_name}<br>
            <strong>Date:</strong> {activity_date}<br>
            <a href="{strava_url}" target="_blank">View on Strava</a>
            """
            folium.Popup(popup_content, max_width=300).add_to(polyline)

        except Exception as e:
            print(f"Error reading FIT {fit_file}: {e}")


    # Save map
    m.save(args.output)
    print(f"Saved interactive map to {args.output}")


# CLI

if __name__ == "__main__":
    parser = ArgumentParser(description="Generate an interactive map from GPX and FIT files")
    parser.add_argument("--gpx_dir", default="gpx", help="Directory containing GPX files")
    parser.add_argument("--fit_dir", default="fit", help="Directory containing FIT files")
    parser.add_argument("--output", default="index.html", help="Output HTML map file")
    args = parser.parse_args()
    main(args)




# Faster code, only for gpx files!
# import os
# import glob
# import numpy as np
# import folium
# from argparse import ArgumentParser, Namespace
# from xml.etree import ElementTree as ET
# from datetime import datetime


# def extract_gpx_info(gpx_file: str) -> tuple:
#     # goal of this func: extract activity name and date from the GPX file
#     tree = ET.parse(gpx_file)
#     root = tree.getroot()


#     namespace = {'gpx': 'http://www.topografix.com/GPX/1/1'}

#     # getting name and date
#     name = root.find('.//gpx:name', namespace).text
#     time = root.find('.//gpx:metadata/gpx:time', namespace).text

#     # parse date
#     date_obj = datetime.strptime(time, '%Y-%m-%dT%H:%M:%SZ')

#     # format the date to make more readable so it presents like "April 20, 2013"
#     formatted_date = date_obj.strftime('%B %d, %Y') 
#     return name, formatted_date


# def main(args: Namespace) -> None:
#     # read GPX trackpoints
#     gpx_files = glob.glob(f'{args.dir}/{args.filter}')

#     #TODO: another file or in here somewhere convert fit to gpx file or just add a case for if it is a fit file
#     if not gpx_files:
#         exit(f'ERROR no data matching {args.dir}/{args.filter}')



#     map_center = [0, 0]
#     m = folium.Map(location=map_center, zoom_start=12)

#     for gpx_file in gpx_files:
#         print(f'Reading {os.path.basename(gpx_file)}')

#         # use helper func to get name and date
#         activity_name, activity_date = extract_gpx_info(gpx_file)

#         lat_lon_data = []
#         with open(gpx_file, encoding='utf-8') as file:
#             for line in file:
#                 if '<trkpt' in line:
#                     l = line.split('"')
#                     lat_lon_data.append([float(l[1]), float(l[3])])

#         lat_lon_data = np.array(lat_lon_data)
#         if lat_lon_data.size == 0:
#             exit(f'ERROR no data in {gpx_file}')
#         print(f'Read {lat_lon_data.shape[0]} trackpoints in {os.path.basename(gpx_file)}')

#         # downsample the data ( make the map load fast!)
#         lat_lon_data = lat_lon_data[::8]  # Here I currently have this number set to 8 which means it will only plot every 8th point.
#         #If you want more detail you can lower this number (map will load slower) and if you want it to be faster you can make this number higher (less detail).

#         # find bounding box for this specific route
#         lat_min, lon_min = np.min(lat_lon_data, axis=0)
#         lat_max, lon_max = np.max(lat_lon_data, axis=0)

#         # update map center (ultimately, the average of all routes)
#         map_center = [np.mean(lat_lon_data[:, 0]), np.mean(lat_lon_data[:, 1])]
#         m.location = map_center

#         #  CSS for tooltip
#         custom_css = """
#         <style>
#             .leaflet-tooltip.custom-tooltip-style {
#                 background-color: #007bff;
#                 color: yellow;
#                 border: 2px solid green;
#                 font-size: 16px;
#                 padding: 8px;
#                 border-radius: 3px;
#             }
#             .leaflet-interactive:focus {
#                 outline: none !important;
#             }
#         </style>
#         """
#         # Inject the CSS into the map (found on google)
#         m.get_root().html.add_child(folium.Element(custom_css))

#         # add GPX data as a polyline (for each ride independently), this is so the user can hover/click anywhere on the route to get more info instead of having specific buttons along the route they have to press to get the info.
#         polyline = folium.PolyLine(
#             locations=lat_lon_data.tolist(),  # list of [lat, lon] points
#             color="blue",  # Here you can change the color of the line
#             weight=2,  # line thickness
#             opacity=0.8, 
#             tooltip=(
#                 '<strong>' + activity_name + '</strong>' + '<br>' + activity_date + '<br>' + 'Click for more info'
#             )
#         ).add_to(m)

#         # We realized the link to every activity is www.strava.com/activities/ (a specific ID number for that activity)
#         #That ID number also happened to be the name ofeach gpx file
#         #Here we are extracting the file name without extension
#         gpx_filename = os.path.basename(gpx_file)
#         activity_id = os.path.splitext(gpx_filename)[0]  # remove the .gpx

#         # create Strava URL
#         strava_url = f'https://www.strava.com/activities/{activity_id}'

#         # popup  with activity name, date, and Strava link
#         popup_content = f"""
#         <strong>Activity:</strong> {activity_name}<br>
#         <strong>Date:</strong> {activity_date}<br>
#         <a href="{strava_url}" target="_blank">View on Strava</a>
#         """

#         # attaching the popup to the polyline (when clicked, shows the activity info)
#         folium.Popup(popup_content, max_width=300).add_to(polyline)

#     # saving the interactive map to HTML file
#     m.save(args.output)
#     print(f'Saved interactive map to {args.output}')


# if __name__ == '__main__':
#     parser = ArgumentParser(description='Generate an interactive line map from GPX data')
#     parser.add_argument('--dir', default='gpx', help='GPX files directory (default: gpx)')
#     parser.add_argument('--filter', default='*.gpx', help='GPX files glob filter (default: *.gpx)')
#     parser.add_argument('--output', default='track_lines_map.html', help='Interactive map output file (default: track_lines_map.html)')
#     args = parser.parse_args()
#     main(args)

