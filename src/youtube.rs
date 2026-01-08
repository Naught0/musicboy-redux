use serde::{Deserialize, Serialize};
use std::process::Stdio;
use tokio::process::Command;
use std::env;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoInfo {
    pub title: String,
    pub url: String,
    pub audio_url: String,
    pub duration: f64,
}

fn get_node_arg() -> String {
    let path = env::var("NODE_PATH").unwrap_or_else(|_| "node".to_string());
    // If it looks like a path, prepend "node:", otherwise assume it's just the binary name
    if path.contains('/') || path.contains('\\') {
        format!("node:{}", path)
    } else {
        "node".to_string()
    }
}

pub async fn get_video_info(url: &str) -> anyhow::Result<VideoInfo> {
    let node_arg = get_node_arg();
    
    let output = Command::new("yt-dlp")
        .args(&[
            "-J",
            "--no-playlist",
            "--js-runtimes", &node_arg,
            "-f", "bestaudio/best",
            url
        ])
        .stdout(Stdio::piped())
        .spawn()
        .map_err(|e| anyhow::anyhow!("Failed to spawn yt-dlp: {}", e))?
        .wait_with_output()
        .await?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(anyhow::anyhow!("yt-dlp error: {}", stderr));
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
    let node_arg = get_node_arg();

    let output = Command::new("yt-dlp")
        .args(&[
            "--flat-playlist", 
            "-J",
            "--js-runtimes", &node_arg, 
            url
        ])
        .stdout(Stdio::piped())
        .spawn()
        .map_err(|e| anyhow::anyhow!("Failed to spawn yt-dlp: {}", e))?
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
