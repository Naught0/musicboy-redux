use redis::AsyncCommands;
use crate::youtube::VideoInfo;

pub struct VideoInfoCache<'a> {
    client: &'a redis::Client,
}

impl<'a> VideoInfoCache<'a> {
    pub fn new(client: &'a redis::Client) -> Self {
        Self { client }
    }

    pub async fn get(&self, url: &str) -> Option<VideoInfo> {
        let mut conn = self.client.get_multiplexed_async_connection().await.ok()?;
        let data: String = conn.get(url).await.ok()?;
        println!("Hit cache for {}", url);
        serde_json::from_str(&data).ok()
    }

    pub async fn set(&self, info: &VideoInfo) -> anyhow::Result<()> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        let data = serde_json::to_string(info)?;
        let _: () = conn.set(info.url.clone(), data).await?;
        Ok(())
    }
}
