from services import auth

def get_subscriptions(limit=None):
    """Fetches the authenticated user's subscriptions.
    If limit is None, fetches ALL subscriptions (with pagination).
    """
    try:
        youtube = auth.get_youtube_service()
        subscriptions = []
        next_page_token = None
        
        while True:
            request = youtube.subscriptions().list(
                part="snippet",
                mine=True,
                maxResults=50,
                order="alphabetical",
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response.get("items", []):
                subscriptions.append({
                    "id": item["snippet"]["resourceId"]["channelId"],
                    "title": item["snippet"]["title"],
                    "thumbnail": item["snippet"]["thumbnails"]["default"]["url"]
                })
            
            next_page_token = response.get("nextPageToken")
            
            # If limit is set and we reached it, stop
            if limit and len(subscriptions) >= limit:
                subscriptions = subscriptions[:limit]
                break
                
            # If no more pages, stop
            if not next_page_token:
                break
                
        return subscriptions
    except Exception as e:
        print(f"Error fetching subscriptions: {e}")
        return []

def get_channel_videos(channel_id):
    """Fetches recent videos from a specific channel."""
    try:
        youtube = auth.get_youtube_service()
        videos = []
        
        # 1. Get the Uploads playlist ID for the channel
        channel_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        
        if not channel_response["items"]:
            return []
            
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # 2. Fetch videos from that playlist
        playlist_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=20
        ).execute()
        
        for item in playlist_response.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "thumbnail": snippet["thumbnails"]["medium"]["url"],
                "publishedAt": snippet["publishedAt"],
                "channelTitle": snippet["channelTitle"]
            })
            
        return videos
    except Exception as e:
        print(f"Error fetching channel videos: {e}")
        return []
