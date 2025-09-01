# strava_local_heatmap.py
This project is a modification of a script by Remi Salmon, which originally created a static heatmap from GPX files. We adapted the code to meet our specific needs, transforming it into a dynamic map that visualizes ride data interactively. In addition, we added functionality to display details about each ride, including a link to the Strava activity page. The final component we added was the ability to do this with both GPX files and FIT files.


## Usage

* Before running the script, make sure to install the required external libraries: folium, pandas, fitparse, and numpy. You can do this using pip by typing the following command into the terminal: 'pip install numpy pandas folium fitparse'
* By default, the program looks for a folder called gpx in the same directory as the Python script, so the easiest way to get started is to download your GPX files from Strava and place them into a folder named gpx and put the FIT files in a folder called fit. Within the starva downloaded data, there is an activities.csv, this should also get placed within your project folder. Your project structure should look like this:

```text
overall-project-folder/
├── strava_local_heatmap.py # Main Python script
├── activities.csv # Strava activities file (from export)
├── gpx/ # Folder containing GPX files
│ ├── activity1.gpx
│ ├── activity2.gpx
│ └── ...
└── fit/ # Folder containing FIT or FIT.GZ files
├── activity1.fit
├── activity2.fit.gz
└── ...
```


* Then, run the python file using the following command in the terminal: `python strava_local_heatmap.py`
* This will generate an HTML file with a dynamic map, visualizing all the tracks. The output file will be saved with the name track_lines_map.html
* It can take a while to generate the HTML file, so we recommend starting with just a few GPX and FIT files to make sure everything runs smoothly before adding your full dataset.
* Enjoy!
