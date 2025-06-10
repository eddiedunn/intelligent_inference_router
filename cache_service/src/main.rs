use std::{collections::HashMap, net::SocketAddr, sync::Arc, time::{Duration, Instant}};

use axum::{routing::{get, put}, Router, extract::{Path, State, Query}, body::Bytes, response::IntoResponse, http::StatusCode};
use serde::Deserialize;
use tokio::sync::RwLock;

type Store = Arc<RwLock<HashMap<String, (Instant, Bytes)>>>;

#[derive(Deserialize)]
struct PutParams {
    ttl: Option<u64>,
}

async fn get_key(Path(key): Path<String>, State(store): State<Store>) -> impl IntoResponse {
    let mut store = store.write().await;
    if let Some((expires, value)) = store.get(&key).cloned() {
        if Instant::now() < expires {
            return (StatusCode::OK, value).into_response();
        } else {
            store.remove(&key);
        }
    }
    StatusCode::NOT_FOUND.into_response()
}

async fn put_key(
    Path(key): Path<String>,
    Query(params): Query<PutParams>,
    State(store): State<Store>,
    body: Bytes,
) -> impl IntoResponse {
    let ttl = params.ttl.unwrap_or(300);
    let expires = Instant::now() + Duration::from_secs(ttl);
    store.write().await.insert(key, (expires, body));
    StatusCode::OK
}

#[tokio::main]
async fn main() {
    let store: Store = Arc::new(RwLock::new(HashMap::new()));
    let app = Router::new()
        .route("/:key", get(get_key).put(put_key))
        .with_state(store);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8600));
    println!("Listening on {addr}");
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}
