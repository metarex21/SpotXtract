import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
from tqdm import tqdm
import glob
import os
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

client_id = config['DEFAULT']['client_id']
client_secret = config['DEFAULT']['client_secret']

# Authenticate your app
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def search_track(artist_name, track_name):
    query = f'artist:{artist_name} track:{track_name}'
    try:
        results = sp.search(q=query, type='track', limit=1)

        if results['tracks']['items']:
            track_info = results['tracks']['items'][0]
            track_id = track_info['id']
            return track_id
        else:
            return None
    except Exception as e:
        print(f"Error occurred while searching for the track: {e}")
        return None
    
def fetch_audio_features(track_id):
    try:
        audio_features = sp.audio_features(track_id)[0]
        return audio_features
    except Exception as e:
        print(f"Error occurred while fetching audio features: {e}")
        return None

def fetch_genre(track_id):
    try:
        track_info = sp.track(track_id)
        if track_info['artists']:
            artist_id = track_info['artists'][0]['id']
            artist_info = sp.artist(artist_id)
            if artist_info['genres']:
                genre = artist_info['genres'][0]
                return genre
        return None
    except Exception as e:
        print(f"Error occurred while fetching genre: {e}")
        return None
    
def features_extractor(csv_file):
    df = pd.read_csv(csv_file)
    artist_names = df['artistName'].tolist()
    track_names = df['trackName'].tolist()
    genre_list = []
    audio_features_list = []

    progress_bar = tqdm(total=len(artist_names), desc='Processing')

    for i in range(len(artist_names)):
        track_id = search_track(artist_names[i], track_names[i])

        if track_id:
            genre = fetch_genre(track_id)
            genre_list.append(genre)

            audio_features = fetch_audio_features(track_id)
            audio_features_list.append(audio_features)
        else:
            genre_list.append(None)
            audio_features_list.append({})  # Empty dictionary for None audio features

        progress_bar.set_postfix(file=f'{csv_file}')
        progress_bar.update(1)

    progress_bar.close()

    audio_feature_columns = ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness',
                             'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo',
                             'type', 'id', 'uri', 'track_href', 'analysis_url', 'duration_ms',
                             'time_signature']

    for column in audio_feature_columns:
        df[column] = [af.get(column) if af else None for af in audio_features_list]

    df['genre'] = genre_list

    df.to_csv(csv_file, index=False)

    return None

# Read the CSV file
data = pd.read_csv('TotalStreamingHistory.csv')

# Group by track name and artist name, and sum the msPlayed values
grouped_data = data.groupby(['trackName', 'artistName']).agg({'msPlayed': 'sum'}).reset_index()

# Save the reduced data to a new CSV file
grouped_data.to_csv('ReducedStreamingHistory.csv', index=False)

data=pd.read_csv('ReducedStreamingHistory.csv')

# Define the list of column names
columns = ['genre', 'danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness',
           'instrumentalness', 'liveness', 'valence', 'tempo', 'type', 'id', 'uri', 'track_href',
           'analysis_url', 'duration_ms', 'time_signature']

# Add the empty columns to the DataFrame
for column in columns:
    data[column] = None

# Save the updated DataFrame back to the CSV file
data.to_csv('ReducedStreamingHistory.csv', index=False)

def split_csv(input_csv, output_prefix, num_files):
    df = pd.read_csv(input_csv)
    total_rows = len(df)
    rows_per_file = total_rows // num_files

    for i in range(num_files):
        start_row = i * rows_per_file
        end_row = start_row + rows_per_file

        if i == num_files - 1:
            # For the last file, include any remaining rows
            end_row = total_rows

        output_csv = f"{output_prefix}_{i+1}.csv"
        df_subset = df[start_row:end_row]
        df_subset.to_csv(output_csv, index=False)

    print(f"CSV file '{input_csv}' successfully split into {num_files} files.")

def merge_csv_files(input_prefix, output_csv):
    file_pattern = f"{input_prefix}_*.csv"
    file_list = glob.glob(file_pattern)

    dfs = []
    for file in file_list:
        df = pd.read_csv(file)
        dfs.append(df)

    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df.to_csv(output_csv, index=False)

    print(f"CSV files merged into '{output_csv}'.")

input_csv = 'ReducedStreamingHistory.csv'  # Replace with your input CSV filename
output_prefix = 'ReducedStreamingHistory'  # Replace with the desired output filename prefix
num_files = 10  # Number of files to split into

split_csv(input_csv, output_prefix, num_files)

start=int(input("Enter starting batch number:")) 
for i in range(start,num_files+1):
    csv= f"{output_prefix}_{i}.csv"
    # Apply feature extractor to the new CSV file
    features_extractor(csv)

input_prefix = 'ReducedStreamingHistory'  
output_csv = 'Spotify_Song_Attributes.csv'  

merge_csv_files(input_prefix, output_csv)

for i in range(1, 11):
    # Construct the file name
    file_name = f"ReducedStreamingHistory_{i}.csv"
    if os.path.exists(file_name):
        os.remove(file_name)

file_name=f"TotalStreamingHistory.csv"
if os.path.exists(file_name):
        os.remove(file_name)

file_name=f"ReducedStreamingHistory.csv"
if os.path.exists(file_name):
        os.remove(file_name)

print("Successfully deleted additional files.")
