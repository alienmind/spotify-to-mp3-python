# Spotify to MP3

A Python application that converts Spotify playlists to MP3 files by searching and downloading matching tracks from YouTube.

## Setup

### 1. Install System Dependencies

The application requires FFmpeg for audio conversion and processing. Install it using your system's package manager:

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Windows
Download and install FFmpeg from the [official website](https://ffmpeg.org/download.html) or use Chocolatey:
```bash
choco install ffmpeg
```

### 2. Set Up Python Environment with uv

`uv` is a fast, drop-in replacement for pip/pip-tools and virtualenv. Here's how to set up your project with it:

#### Install uv

```bash
# Using pip
pip install uv

# Using Homebrew (macOS)
brew install uv
```

#### Create and Activate Virtual Environment

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

#### Install Dependencies

With the virtual environment activated, install the required Python packages:

```bash
uv pip install spotipy youtube-search-python yt-dlp mutagen
```

Alternatively, if you have a requirements.txt file:

```bash
uv pip install -r requirements.txt
```

### 3. Create a config.ini file

The application requires Spotify API credentials to function. Follow these steps to create your `config.ini` file:

1. Visit the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and log in with your Spotify account.

2. Click "Create an App" and fill in the required information:
   - App name: SpotifyToMP3 (or any name you prefer)
   - App description: Personal tool to manage playlists
   - Redirect URI: http://localhost:8888/callback

3. After creating the app, you'll see your Client ID and Client Secret on the dashboard.

4. Create a file named `config.ini` in the root directory of this project with the following structure:

```ini
[Settings]
client_id=your_client_id_here
client_secret=your_client_secret_here
username=your_spotify_username_here
```

Replace the placeholders with your actual Spotify information:
- `your_client_id_here`: The Client ID from the Spotify Developer Dashboard
- `your_client_secret_here`: The Client Secret from the Spotify Developer Dashboard
- `your_spotify_username_here`: Your Spotify username

### 4. Authorization

The first time you run the application, it will open a web browser asking you to authorize the application to access your Spotify data. After authorization, you'll be redirected to the callback URL, which might show an error page (this is normal). Copy the entire URL from your browser's address bar and paste it back into the terminal when prompted.

## Usage

```bash
python spotify_to_mp3.py <playlist_id>
```

Where `<playlist_id>` is the Spotify playlist ID you want to convert. You can find the playlist ID in the Spotify URL, e.g., https://open.spotify.com/playlist/37i9dQZF1DZ06evO45P0Eo (the ID is the part after "playlist/").

## Notes

- The program will create a text file with the same name as the playlist, containing all tracks.
- It will then search YouTube for each track and download the best matching audio.
- The MP3 files will be saved in the current directory with artist and track information.
- Album art will be extracted from YouTube thumbnails and embedded in the MP3 files.

## Troubleshooting

- If you encounter HTTP 403 errors, the application will automatically retry with exponential backoff.
- If problems persist, try running the script later as YouTube may be rate-limiting your IP address.
- Make sure your `config.ini` file contains the correct credentials and is properly formatted.
