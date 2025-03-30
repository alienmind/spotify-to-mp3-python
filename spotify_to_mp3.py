# Downloads a Spotify playlist into a folder of MP3 tracks
# Jason Chen, 21 June 2020

import os
import spotipy
import spotipy.oauth2 as oauth2
import yt_dlp
from youtube_search import YoutubeSearch
import multiprocessing
import urllib.request
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
import time

# **************PLEASE READ THE README.md FOR USE INSTRUCTIONS**************n
def write_tracks(file, tracks):
    # Check if tracks contains 'items' directly or if it's a different structure
    if 'items' in tracks:
        track_items = tracks['items']
    else:
        # If tracks is already a list of items
        track_items = tracks
    
    for item in track_items:
        if 'track' in item:
            track = item['track']
        else:
            track = item  # In case the track data is directly available
            
        # Continue with the existing logic for processing tracks
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        
        file.write(f"{artist_name} - {track_name}\n")
    
    return


def write_playlist(username: str, playlist_id: str):
    results = spotify.user_playlist(username, playlist_id, fields='tracks,next,name')
    playlist_name = results['name']
    text_file_name = u'{0}.txt'.format(playlist_name, ok='-_()[]{}')
    print(u'Writing {0} tracks to {1}.'.format(results['tracks']['total'], text_file_name))
    tracks = results['tracks']
    
    # Open the file first, then pass the file object to write_tracks
    with open(text_file_name, 'w', encoding='utf-8') as file:
        write_tracks(file, tracks)

    imgURLs = []
    for item in tracks['items']:
        imgURLs.append(item['track']['album']['images'][0]['url'])
    return playlist_name, imgURLs

def find_and_download_songs(reference_file: str):
    TOTAL_ATTEMPTS = 10
    DOWNLOAD_RETRIES = 3  # Number of times to retry downloads
    
    with open(reference_file, "r", encoding='utf-8') as file:
        for line in file:
            # The format from write_tracks is "artist_name - track_name"
            # Split by the first occurrence of " - "
            if " - " in line:
                artist, name = line.strip().split(" - ", 1)
            else:
                # Skip malformed lines
                print(f"Skipping malformed line: {line.strip()}")
                continue
                
            # Getting album art URL from the tracks list
            # Since we don't have it in the text file, we need to search for it again
            text_to_search = f"{artist} - {name}"
            
            # Search for the track again to get its URL
            best_url = None
            attempts_left = TOTAL_ATTEMPTS
            while attempts_left > 0:
                try:
                    results_list = YoutubeSearch(text_to_search, max_results=1).to_dict()
                    best_url = "https://www.youtube.com{}".format(results_list[0]['url_suffix'])
                    break
                except (IndexError, KeyError) as e:
                    attempts_left -= 1
                    print("No valid URLs found for {}, trying again ({} attempts left). Error: {}".format(
                        text_to_search, attempts_left, str(e)))
                # Add delay between search attempts to avoid rate limiting
                time.sleep(1)
            if best_url is None:
                print("No valid URLs found for {}, skipping track.".format(text_to_search))
                continue

            # Create safe filenames by replacing problematic characters
            safe_name = name.replace('｜', '-').replace('|', '-').replace(':', '-').replace('?', '').replace('"', '')
            # Replace any other problematic characters
            safe_name = ''.join(c for c in safe_name if c.isprintable() and c not in '<>:"/\\|?*')
            
            # For album art, we'll need to use a placeholder or get it from YouTube
            album_art_url = None
            for attempt in range(DOWNLOAD_RETRIES):
                try:
                    # Download YouTube thumbnail to use as album art
                    with yt_dlp.YoutubeDL({'quiet': True, 'socket_timeout': 30}) as ydl:
                        info = ydl.extract_info(best_url, download=False)
                        if 'thumbnail' in info:
                            album_art_url = info['thumbnail']
                            print(f"Using YouTube thumbnail as album art for {text_to_search}")
                            break
                        else:
                            raise Exception("No thumbnail found")
                except Exception as e:
                    print(f"Error getting album art (attempt {attempt+1}/{DOWNLOAD_RETRIES}): {str(e)}")
                    # Wait before retrying
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
            
            if album_art_url is None:
                print(f"Could not get album art for {text_to_search}, skipping album art")
                continue

            try:
                print("Initiating download for Image {}.".format(album_art_url))
                # Use a timeout for the request
                from urllib.error import HTTPError, URLError
                
                art_download_success = False
                for attempt in range(DOWNLOAD_RETRIES):
                    try:
                        req = urllib.request.Request(
                            album_art_url,
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                        )
                        with urllib.request.urlopen(req, timeout=30) as response, open('{}.jpg'.format(safe_name), 'wb') as f:
                            f.write(response.read())
                        art_download_success = True
                        break
                    except (HTTPError, URLError) as e:
                        print(f"HTTP error downloading album art (attempt {attempt+1}/{DOWNLOAD_RETRIES}): {str(e)}")
                        time.sleep(2 * (attempt + 1))  # Exponential backoff
                    except Exception as e:
                        print(f"Error downloading album art (attempt {attempt+1}/{DOWNLOAD_RETRIES}): {str(e)}")
                        time.sleep(2 * (attempt + 1))
                
                if not art_download_success:
                    print(f"Failed to download album art after {DOWNLOAD_RETRIES} attempts, skipping album art")
                    continue
            except Exception as e:
                print(f"Error saving album art: {str(e)}")
                continue

            # Run you-get to fetch and download the link's audio
            print("Initiating download for {}.".format(text_to_search))
            
            download_success = False
            for attempt in range(DOWNLOAD_RETRIES):
                try:
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': '%(title)s',     #name the file the ID of the video
                        'embedthumbnail': True,
                        'socket_timeout': 30,  # Add timeout 
                        'retries': 5,          # Internal retries
                        'fragment_retries': 5, # Retry fragments
                        'skip_unavailable_fragments': True,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }, {
                            'key': 'FFmpegMetadata',
                        }]
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info([best_url][0], download=True)
                    download_success = True
                    break
                except Exception as e:
                    print(f"Download error (attempt {attempt+1}/{DOWNLOAD_RETRIES}): {str(e)}")
                    time.sleep(5 * (attempt + 1))  # Longer backoff for main content
            
            if not download_success:
                print(f"Failed to download {text_to_search} after {DOWNLOAD_RETRIES} attempts, skipping track")
                try:
                    # Clean up album art if we couldn't download the audio
                    if os.path.exists(f"{safe_name}.jpg"):
                        os.remove(f"{safe_name}.jpg")
                except:
                    pass
                continue

            # extract the name of the downloaded file from the info_dict
            filename = ydl.prepare_filename(info_dict)
            
            # For safety, make sure the filename has a clean extension
            if not filename.endswith('.mp3'):
                mp3_filename = filename + '.mp3'
            else:
                mp3_filename = filename
                
            print(f"The downloaded file name is: {filename}")

            # Try to locate the MP3 file, checking both the original filename and our safe version
            print('Adding Cover Image...')
            
            try:
                audio = MP3(mp3_filename, ID3=ID3)
            except Exception as e:
                print(f"Error opening {mp3_filename}: {e}")
                # Try to find the actual file that was created
                import glob
                possible_files = glob.glob(f"{os.path.splitext(filename)[0]}*.mp3")
                if possible_files:
                    mp3_filename = possible_files[0]
                    print(f"Found alternative file: {mp3_filename}")
                    audio = MP3(mp3_filename, ID3=ID3)
                else:
                    print(f"Could not find any MP3 file for {filename}")
                    continue
                
            try:
                audio.add_tags()
            except error:
                pass

            try:
                audio.tags.add(
                    APIC(
                        encoding=3,  # 3 is for utf-8
                        mime="image/jpeg",  # can be image/jpeg or image/png
                        type=3,  # 3 is for the cover image
                        desc='Cover',
                        data=open("{}.jpg".format(safe_name), mode='rb').read()
                    )
                )
                audio.save()
                
                # Only remove the jpg file if everything succeeded
                if os.path.exists(f"{safe_name}.jpg"):
                    os.remove("{}.jpg".format(safe_name))
            except Exception as e:
                print(f"Error adding cover image: {e}")
                # Don't remove the jpg file in case of error




# Multiprocessed implementation of find_and_download_songs
# This method is responsible for manging and distributing the multi-core workload
def multicore_find_and_download_songs(reference_file: str, cpu_count: int):
    # Extract songs from the reference file

    lines = []
    with open(reference_file, "r", encoding='utf-8') as file:
        for line in file:
            lines.append(line)

    # Process allocation of songs per cpu
    number_of_songs = len(lines)
    songs_per_cpu = number_of_songs // cpu_count

    # Calculates number of songs that dont evenly fit into the cpu list
    # i.e. 4 cores and 5 songs, one core will have to process 1 extra song
    extra_songs = number_of_songs - (cpu_count * songs_per_cpu)

    # Create a list of number of songs which by index allocates it to a cpu
    # 4 core cpu and 5 songs [2, 1, 1, 1] where each item is the number of songs
    #                   Core 0^ 1^ 2^ 3^
    cpu_count_list = []
    for cpu in range(cpu_count):
        songs = songs_per_cpu
        if cpu < extra_songs:
            songs = songs + 1
        cpu_count_list.append(songs)

    # Based on the cpu song allocation list split up the reference file
    index = 0
    file_segments = []
    for cpu in cpu_count_list:
        right = cpu + index
        segment = lines[index:right]
        index = index + cpu
        file_segments.append(segment)

    # Prepares all of the seperate processes before starting them
    # Pass each process a new shorter list of songs vs 1 process being handed all of the songs
    processes = []
    segment_index = 0
    for segment in file_segments:
        p = multiprocessing.Process(target = multicore_handler, args=(segment, segment_index))
        processes.append(p)
        segment_index = segment_index + 1

    # Start the processes
    for p in processes:
        p.start()

    # Wait for the processes to complete and exit as a group
    for p in processes:
        p.join()

# Just a wrapper around the original find_and_download_songs method to ensure future compatibility
# Preserves the same functionality just allows for several shorter lists to be used and cleaned up
def multicore_handler(reference_list: list, segment_index: int):
    # Create reference filename based off of the process id (segment_index)
    reference_filename = "{}.txt".format(segment_index)

    # Write the reference_list to a new "reference_file" to enable compatibility
    with open(reference_filename, 'w+', encoding='utf-8') as file_out:
        for line in reference_list:
            file_out.write(line)

    # Call the original find_and_download method
    find_and_download_songs(reference_filename)

    # Clean up the extra list that was generated
    if(os.path.exists(reference_filename)):
        os.remove(reference_filename)


# This is prompt to handle the multicore queries
# An effort has been made to create an easily automated interface
# Autoeneable: bool allows for no prompts and defaults to max core usage
# Maxcores: int allows for automation of set number of cores to be used
# Buffercores: int allows for an allocation of unused cores (default 1)
def enable_multicore(autoenable=False, maxcores=None, buffercores=1):
    native_cpu_count = multiprocessing.cpu_count() - buffercores
    if autoenable:
        if maxcores:
            if(maxcores <= native_cpu_count):
                return maxcores
            else:
                print("Too many cores requested, single core operation fallback")
                return 1
        return multiprocessing.cpu_count() - 1
    multicore_query = input("Enable multiprocessing (Y or N): ")
    if multicore_query not in ["Y","y","Yes","YES","YEs",'yes']:
        return 1
    core_count_query = int(input("Max core count (0 for allcores): "))
    if(core_count_query == 0):
        return native_cpu_count
    if(core_count_query <= native_cpu_count):
        return core_count_query
    else:
        print("Too many cores requested, single core operation fallback")
        return 1

if __name__ == "__main__":
    # Parameters
    print("Please read README.md for use instructions.")
    if os.path.isfile('config.ini'):
        import configparser
        config = configparser.ConfigParser()
        config.read("config.ini")
        client_id = config["Settings"]["client_id"]
        client_secret = config["Settings"]["client_secret"]
        username = config["Settings"]["username"]
    else:
        client_id = input("Client ID: ")
        client_secret = input("Client secret: ")
        username = input("Spotify username: ")
    playlist_uri = input("Playlist URI/Link: ")
    if playlist_uri.find("https://open.spotify.com/playlist/") != -1:
        playlist_uri = playlist_uri.replace("https://open.spotify.com/playlist/", "")
    multicore_support = enable_multicore(autoenable=False, maxcores=None, buffercores=1)
    auth_manager = oauth2.SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    playlist_name, albumArtUrls = write_playlist(username, playlist_uri)
    reference_file = "{}.txt".format(playlist_name)
    # Create the playlist folder
    if not os.path.exists(playlist_name):
        os.makedirs(playlist_name)
    os.rename(reference_file, playlist_name + "/" + reference_file)
    os.chdir(playlist_name)
    # Enable multicore support
    if multicore_support > 1:
        multicore_find_and_download_songs(reference_file, multicore_support)
    else:
        find_and_download_songs(reference_file)
    os.remove(f'{reference_file}')
    print("Operation complete.")