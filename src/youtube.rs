use rusty_ytdl::{Video, VideoOptions, VideoQuality, VideoSearchOptions};
// Fix: Import Playlist from the 'search' module as suggested by the compiler
use rusty_ytdl::search::Playlist; 
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoInfo {
    pub title: String,
    pub url: String,
    pub audio_url: String,
    pub duration: f64,
}

pub async fn get_video_info(url: &str) -> anyhow::Result<VideoInfo> {
    // Initialize with options to prefer audio
    let video = Video::new_with_options(
        url,
        VideoOptions {
            quality: VideoQuality::HighestAudio,
            filter: VideoSearchOptions::Audio,
            ..Default::default()
        },
    )?;

    // Fetch info
    let info = video.get_info().await?;
    let details = &info.video_details;

    // Find best audio format
    let formats = info.formats;
    let best_format = formats
        .iter()
        .filter(|f| f.has_audio)
        .max_by_key(|f| f.audio_bitrate.unwrap_or(0))
        .ok_or_else(|| anyhow::anyhow!("No audio format found"))?;

    let duration = details.length_seconds.parse::<f64>().unwrap_or(0.0);

    Ok(VideoInfo {
        title: details.title.clone(),
        url: details.video_url.clone(),
        audio_url: best_format.url.clone(),
        duration,
    })
}

pub async fn get_playlist_urls(url: &str) -> anyhow::Result<Vec<String>> {
    // Check if it looks like a playlist
    if url.contains("list=") {
        // Fix: Use the imported 'Playlist' struct directly
        let playlist = Playlist::get(url, None).await?;
        let urls = playlist
            .videos
            .iter()
            .map(|v| v.url.clone())
            .collect();
        Ok(urls)
    } else {
        Ok(vec![url.to_string()])
    }
}
