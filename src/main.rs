mod cache;
mod commands;
mod player;
mod utils;
mod youtube;

use dashmap::DashMap;
use poise::serenity_prelude as serenity;
use redis::Client as RedisClient;
use songbird::SerenityInit;
use std::{env, sync::Arc};
use tokio::sync::Mutex;

use player::PlayerState;

pub struct Data {
    pub redis: RedisClient,
    pub player_states: DashMap<serenity::GuildId, Arc<Mutex<PlayerState>>>,
}

pub type Error = Box<dyn std::error::Error + Send + Sync>;
pub type Context<'a> = poise::Context<'a, Data, Error>;

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();
    tracing_subscriber::fmt::init();

    let redis_url = env::var("REDIS_URL").unwrap_or_else(|_| "redis://localhost:6379".to_string());
    let redis_client = RedisClient::open(redis_url).expect("Invalid Redis URL");

    let token = env::var("BOT_TOKEN").expect("missing BOT_TOKEN");
    let intents = serenity::GatewayIntents::non_privileged() | serenity::GatewayIntents::MESSAGE_CONTENT;

    let framework = poise::Framework::builder()
        .options(poise::FrameworkOptions {
            commands: commands::all_commands(),
            prefix_options: poise::PrefixFrameworkOptions {
                prefix: Some("-".into()),
                additional_prefixes: vec![poise::Prefix::Literal("!!")],
                ..Default::default()
            },
            ..Default::default()
        })
        .setup(move |_ctx, _ready, _framework| {
            Box::pin(async move {
                Ok(Data {
                    redis: redis_client,
                    player_states: DashMap::new(),
                })
            })
        })
        .build();

    let client = serenity::Client::builder(token, intents)
        .framework(framework)
        .register_songbird()
        .await;

    client.expect("Err creating client").start().await.expect("Err starting client");
}
