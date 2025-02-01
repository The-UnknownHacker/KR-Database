# Carnatic Music Database API Documentation

## Authentication
All API endpoints require an API key to be passed in the header:
```
X-API-Key: api_key
```

## Base URL
```
http://127.0.0.1:5000
```

## Endpoints

### List All Songs
Get a list of all songs in the database.

```
GET /api/songs
```

#### Response
```json
{
  "status": "success",
  "songs": [
    {
      "id": 1,
      "name": "Song Name",
      "composer": "Composer Name",
      "ragam": "Ragam Name",
      "talam": "Talam Name",
      "category": "Category Name",
      "has_kalpanaswaram": true,
      "has_audio": true,
      "has_notation": true,
      "created_at": "2024-03-20T12:34:56"
    }
  ]
}
```

### Get Song Details
Get details for a specific song by ID.

```
GET /api/songs/<song_id>
```

#### Response
```json
{
  "status": "success",
  "song": {
    "id": 1,
    "name": "Song Name",
    "composer": "Composer Name",
    "ragam": "Ragam Name",
    "talam": "Talam Name",
    "category": "Category Name",
    "has_kalpanaswaram": true,
    "has_audio": true,
    "has_notation": true,
    "created_at": "2024-03-20T12:34:56"
  }
}
```

### Get Song Audio
Download the audio file for a specific song.

```
GET /api/songs/<song_id>/audio
```

#### Response
- Success: Audio file (MP3/WAV)
- Error (404):
```json
{
  "status": "error",
  "message": "No audio file available for this song"
}
```

### Get Song Notation
Download the notation file for a specific song.

```
GET /api/songs/<song_id>/notation
```

#### Response
- Success: PDF file
- Error (404):
```json
{
  "status": "error",
  "message": "No notation file available for this song"
}
```

## Error Responses

### Authentication Errors
```json
{
  "status": "error",
  "message": "No API key provided"
}
```
```json
{
  "status": "error",
  "message": "Invalid API key"
}
```

## Example Usage

Using curl:
```bash
# Set API key
API_KEY="api_key"

# Get all songs
curl http://127.0.0.1:5000/api/songs \
  -H "X-API-Key: $API_KEY"

# Get specific song
curl http://127.0.0.1:5000/api/songs/1 \
  -H "X-API-Key: $API_KEY"

# Download audio file
curl http://127.0.0.1:5000/api/songs/1/audio \
  -H "X-API-Key: $API_KEY" \
  --output song.mp3

# Download notation file
curl http://127.0.0.1:5000/api/songs/1/notation \
  -H "X-API-Key: $API_KEY" \
  --output notation.pdf
```

Using Python:
```python
import requests

API_URL = "http://127.0.0.1:5000"
API_KEY = "api_key"
HEADERS = {"X-API-Key": API_KEY}

# Get all songs
response = requests.get(f"{API_URL}/api/songs", headers=HEADERS)
songs = response.json()["songs"]

# Get specific song
song_id = 1
response = requests.get(f"{API_URL}/api/songs/{song_id}", headers=HEADERS)
song = response.json()["song"]

# Download audio file
response = requests.get(f"{API_URL}/api/songs/{song_id}/audio", headers=HEADERS)
if response.ok:
    with open("song.mp3", "wb") as f:
        f.write(response.content)

# Download notation file
response = requests.get(f"{API_URL}/api/songs/{song_id}/notation", headers=HEADERS)
if response.ok:
    with open("notation.pdf", "wb") as f:
        f.write(response.content)
```