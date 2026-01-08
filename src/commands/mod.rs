use crate::{cache::VideoInfoCache, player::PlayerState, utils, youtube, Context, Error};
use poise::serenity_prelude as serenity;
use songbird::Call;
use std::sync::Arc;
use tokio::sync::Mutex;

pub fn all_commands() -> Vec<poise::Command<crate::Data, crate::Error>> {
    vec![
        join(),
        leave(),
        play(),
        skip(),
        pause(),
        resume(),
        queue(),
        now_playing(),
        shuffle(),
        volume(),
    ]
}

async fn get_state(ctx: &Context<'_>) -> Option<Arc<Mutex<PlayerState>>> {
    let guild_id = ctx.guild_id()?;
    let map = &ctx.data().player_states;
    
    if !map.contains_key(&guild_id) {
        map.insert(guild_id, Arc::new(Mutex::new(PlayerState::new())));
    }
    
    map.get(&guild_id).map(|r| r.value().clone())
}

async fn play_next_in_queue(
    handler: Arc<Mutex<Call>>,
    state: Arc<Mutex<PlayerState>>,
) {
    let mut state_guard = state.lock().await;
    
    state_guard.current_handle = None;

    if let Some(track_info) = state_guard.pop_next() {
        let mut handler_guard = handler.lock().await;
        
        let src = songbird::input::YoutubeDl::new(reqwest::Client::new(), track_info.url.clone());
        let handle = handler_guard.play_input(src.into());
        
        state_guard.current_handle = Some(handle);
    }
}

#[poise::command(slash_command, prefix_command)]
async fn join(ctx: Context<'_>) -> Result<(), Error> {
    let guild_id = ctx.guild_id().ok_or("Not in a guild")?;
    let channel_id = ctx
        .guild()
        .and_then(|g| g.voice_states.get(&ctx.author().id).and_then(|vs| vs.channel_id))
        .ok_or("You are not in a voice channel")?;

    let manager = songbird::get(ctx.serenity_context())
        .await
        .ok_or("Songbird Voice client not initialized")?
        .clone();

    let _ = manager.join(guild_id, channel_id).await;
    ctx.say("Joined voice channel").await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("stop"))]
async fn leave(ctx: Context<'_>) -> Result<(), Error> {
    let guild_id = ctx.guild_id().ok_or("Not in a guild")?;
    let manager = songbird::get(ctx.serenity_context())
        .await
        .ok_or("Songbird Voice client not initialized")?
        .clone();

    if manager.leave(guild_id).await.is_ok() {
        ctx.say("Left voice channel").await?;
    }
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("p"))]
async fn play(ctx: Context<'_>, #[rest] url: Option<String>) -> Result<(), Error> {
    let guild_id = ctx.guild_id().ok_or("Not in a guild")?;
    let state = get_state(&ctx).await.unwrap();
    
    if let Some(manager) = songbird::get(ctx.serenity_context()).await {
        if manager.get(guild_id).is_none() {
             let channel_id = ctx
                .guild()
                .and_then(|g| g.voice_states.get(&ctx.author().id).and_then(|vs| vs.channel_id));
            if let Some(cid) = channel_id {
                let _ = manager.join(guild_id, cid).await;
            }
        }
    }

    let url = match url {
        Some(u) => u,
        None => {
             if let Some(manager) = songbird::get(ctx.serenity_context()).await {
                if let Some(handler_lock) = manager.get(guild_id) {
                     play_next_in_queue(handler_lock, state).await;
                }
             }
             return Ok(());
        }
    };

    ctx.say("🔄 Processing...").await?;

    let urls = youtube::get_playlist_urls(&url).await?;
    let cache = VideoInfoCache::new(&ctx.data().redis);
    let mut added_count = 0;

    for u in urls {
        let info = if let Some(cached) = cache.get(&u).await {
            cached
        } else {
            let fetched = youtube::get_video_info(&u).await?;
            let _ = cache.set(&fetched).await;
            fetched
        };

        let mut lock = state.lock().await;
        lock.add_track(info);
        added_count += 1;
    }

    if let Some(manager) = songbird::get(ctx.serenity_context()).await {
        if let Some(handler_lock) = manager.get(guild_id) {
            let should_play = {
                let guard = state.lock().await;
                match &guard.current_handle {
                    None => true,
                    Some(h) => {
                        match h.get_info().await {
                            Ok(info) => matches!(info.playing, songbird::tracks::PlayMode::Stop | songbird::tracks::PlayMode::End),
                            Err(_) => true,
                        }
                    }
                }
            };

            if should_play {
                play_next_in_queue(handler_lock.clone(), state.clone()).await;
            }
        }
    }

    ctx.say(format!("✅ Added {} track(s) to queue", added_count)).await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("next"))]
async fn skip(ctx: Context<'_>) -> Result<(), Error> {
    let guild_id = ctx.guild_id().ok_or("Not in a guild")?;
    
    if let Some(manager) = songbird::get(ctx.serenity_context()).await {
        if let Some(handler_lock) = manager.get(guild_id) {
            let state = get_state(&ctx).await.unwrap();
            
            {
                let guard = state.lock().await;
                if let Some(handle) = &guard.current_handle {
                    let _ = handle.stop();
                }
            }
            
            play_next_in_queue(handler_lock.clone(), state).await;
            ctx.say("Skipped!").await?;
        }
    }
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("q"))]
async fn queue(ctx: Context<'_>) -> Result<(), Error> {
    let state_arc = get_state(&ctx).await.unwrap();
    let state = state_arc.lock().await;

    if state.queue.is_empty() && state.current_track.is_none() {
         ctx.say("Queue is empty").await?;
         return Ok(());
    }

    let mut description = String::new();
    for (i, track) in state.queue.iter().take(10).enumerate() {
        description.push_str(&format!("{}. {}\n", i + 1, track.title));
    }

    let embed = serenity::CreateEmbed::new()
        .title("Queue")
        .description(description)
        .footer(serenity::CreateEmbedFooter::new(format!("Total: {}", state.queue.len())));

    ctx.send(poise::CreateReply::default().embed(embed)).await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("np"))]
async fn now_playing(ctx: Context<'_>) -> Result<(), Error> {
    let state_arc = get_state(&ctx).await.unwrap();
    let state = state_arc.lock().await;

    let mut progress = 0.0;
    
    if let Some(handle) = &state.current_handle {
        if let Ok(info) = handle.get_info().await {
            progress = info.position.as_secs_f64();
        }
    }

    let embed = utils::create_np_embed(&state, progress);
    ctx.send(poise::CreateReply::default().embed(embed)).await?;
    Ok(())
}

#[poise::command(slash_command, prefix_command)]
async fn pause(ctx: Context<'_>) -> Result<(), Error> {
    let state_arc = get_state(&ctx).await.unwrap();
    let state = state_arc.lock().await;
    
    if let Some(handle) = &state.current_handle {
        let _ = handle.pause();
        ctx.say("Paused").await?;
    }
    Ok(())
}

#[poise::command(slash_command, prefix_command)]
async fn resume(ctx: Context<'_>) -> Result<(), Error> {
    let state_arc = get_state(&ctx).await.unwrap();
    let state = state_arc.lock().await;
    
    if let Some(handle) = &state.current_handle {
        let _ = handle.play();
        ctx.say("Resumed").await?;
    }
    Ok(())
}

#[poise::command(slash_command, prefix_command)]
async fn shuffle(ctx: Context<'_>) -> Result<(), Error> {
    let state_arc = get_state(&ctx).await.unwrap();
    let mut state = state_arc.lock().await;
    let is_shuffled = state.toggle_shuffle();
    
    if is_shuffled {
        ctx.say("🔀 Shuffled").await?;
    } else {
        ctx.say("↩️ Unshuffled").await?;
    }
    Ok(())
}

#[poise::command(slash_command, prefix_command, aliases("vol", "v"))]
async fn volume(ctx: Context<'_>, level: u32) -> Result<(), Error> {
    let state_arc = get_state(&ctx).await.unwrap();
    let state = state_arc.lock().await;
    
    if level > 100 {
        ctx.say("Volume must be 0-100").await?;
        return Ok(());
    }

    if let Some(handle) = &state.current_handle {
        let _ = handle.set_volume(level as f32 / 100.0);
        ctx.say(format!("🔊 Volume set to {}%", level)).await?;
    }
    Ok(())
}
