use crate::youtube::VideoInfo;
use rand::seq::SliceRandom;
use std::collections::VecDeque;

#[derive(Debug)]
pub struct PlayerState {
    pub playlist: Vec<VideoInfo>,
    pub queue: VecDeque<VideoInfo>,
    pub current_track: Option<VideoInfo>,
    pub is_shuffled: bool,
}

impl PlayerState {
    pub fn new() -> Self {
        Self {
            playlist: Vec::new(),
            queue: VecDeque::new(),
            current_track: None,
            is_shuffled: false,
        }
    }

    pub fn add_track(&mut self, track: VideoInfo) {
        self.playlist.push(track.clone());
        self.queue.push_back(track);
    }

    pub fn pop_next(&mut self) -> Option<VideoInfo> {
        let next = self.queue.pop_front();
        self.current_track = next.clone();
        next
    }

    pub fn toggle_shuffle(&mut self) -> bool {
        self.is_shuffled = !self.is_shuffled;
        
        if self.is_shuffled {
            let mut vec: Vec<VideoInfo> = self.queue.drain(..).collect();
            let mut rng = rand::thread_rng();
            vec.shuffle(&mut rng);
            self.queue = VecDeque::from(vec);
        } else {
            if let Some(current) = &self.current_track {
                if let Some(idx) = self.playlist.iter().position(|x| x.url == current.url) {
                    self.queue = self.playlist.iter().skip(idx + 1).cloned().collect();
                }
            }
        }
        self.is_shuffled
    }
}
