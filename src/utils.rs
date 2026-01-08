use crate::player::PlayerState;
use poise::serenity_prelude::{self as serenity, CreateEmbed};

pub fn seconds_to_time_str(seconds: f64) -> String {
    let seconds = seconds as u64;
    let minutes = seconds / 60;
    let hours = minutes / 60;
    let rem_minutes = minutes % 60;
    let rem_seconds = seconds % 60;

    if hours > 0 {
        format!("{:02}:{:02}:{:02}", hours, rem_minutes, rem_seconds)
    } else {
        format!("{:02}:{:02}", rem_minutes, rem_seconds)
    }
}

pub fn draw_progress_bar(progress: f64, total: f64) -> String {
    let length = 20;
    let percent = if total > 0.0 { progress / total } else { 0.0 };
    let filled = (length as f64 * percent) as usize;
    let empty = length - filled;
    
    format!("{}{}{}", "█".repeat(filled), "▓▒", "░".repeat(empty))
}

pub fn create_np_embed(state: &PlayerState, progress: f64) -> CreateEmbed {
    if let Some(track) = &state.current_track {
        let prog_str = format!("{}/{}", seconds_to_time_str(progress), seconds_to_time_str(track.duration));
        let bar = draw_progress_bar(progress, track.duration);
        
        CreateEmbed::new()
            .title(format!("▶️ {}", track.title))
            .url(&track.url)
            .color(serenity::Color::BLURPLE)
            .description(format!("```\n{}\n{:>23}\n```", bar, prog_str))
    } else {
        CreateEmbed::new().title("Nothing Playing")
    }
}
