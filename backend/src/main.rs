use anyhow::Context;
use hive_agent_backend::settings::AppSettings;
use hive_agent_backend::store::Store;
use hive_agent_backend::{app_state, build_router};
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info,sqlx=warn")),
        )
        .init();

    let settings = AppSettings::from_env();
    let store = Store::connect(&settings).await?;
    let address = format!("{}:{}", settings.host, settings.port);
    tracing::info!(
        store_backend = settings.store_backend.as_str(),
        "Hive Agent Backend listening on http://{address}"
    );

    let listener = tokio::net::TcpListener::bind(&address)
        .await
        .with_context(|| format!("binding {address}"))?;
    axum::serve(listener, build_router(app_state(store, settings)))
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
