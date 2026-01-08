use serde::{Deserialize, Serialize};
use std::process::Stdio;
use tokio::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoInfo {
    pub title: String,
    pub url: String,
    pub audio_url: String,
    pub duration: f64,
}

pub async fn get_video_info(url: &str) -> anyhow::Result<VideoInfo> {
    let output = Command::new("yt-dlp")
        .args(&[
            "-J",
            "--no-playlist",
            "-f", "bestaudio",
            url
        ])
        .stdout(Stdio::piped())
        .spawn()?
        .wait_with_output()
        .await?;

    if !output.status.success() {
        return Err(anyhow::anyhow!("yt-dlp failed"));
    }

    let json: serde_json::Value = serde_json::from_slice(&output.stdout)?;
    
    let title = json["title"].as_str().unwrap_or("Unknown Title").to_string();
    let webpage_url = json["webpage_url"].as_str().unwrap_or(url).to_string();
    let audio_url = json["url"].as_str().unwrap_or("").to_string();
    let duration = json["duration"].as_f64().unwrap_or(0.0);

    Ok(VideoInfo {
        title,
        url: webpage_url,
        audio_url,
        duration,
    })
}

pub async fn get_playlist_urls(url: &str) -> anyhow::Result<Vec<String>> {
    let output = Command::new("yt-dlp")
        .args(&["--flat-playlist", "-J", url])
        .stdout(Stdio::piped())
        .spawn()?
        .wait_with_output()
        .await?;

    let json: serde_json::Value = serde_json::from_slice(&output.stdout)?;
    
    let mut urls = Vec::new();
    if let Some(entries) = json["entries"].as_array() {
        for entry in entries {
            if let Some(id) = entry["id"].as_str() {
                urls.push(format!("https://www.youtube.com/watch?v={}", id));
            }
        }
    } else {
        urls.push(url.to_string());
    }
    
    Ok(urls)
}
