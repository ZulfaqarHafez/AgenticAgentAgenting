use axum::Json;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::{Value, json};

/// An HTTP error rendered as `{"detail": ...}`, matching the FastAPI contract the UI expects.
#[derive(Debug)]
pub struct ApiError {
    pub status: StatusCode,
    pub detail: Value,
}

impl ApiError {
    pub fn new(status: StatusCode, detail: impl Into<Value>) -> Self {
        Self {
            status,
            detail: detail.into(),
        }
    }

    pub fn not_found(message: &str) -> Self {
        Self::new(StatusCode::NOT_FOUND, message)
    }

    pub fn conflict(detail: impl Into<Value>) -> Self {
        Self::new(StatusCode::CONFLICT, detail)
    }

    pub fn unprocessable(detail: impl Into<Value>) -> Self {
        Self::new(StatusCode::UNPROCESSABLE_ENTITY, detail)
    }
}

impl From<anyhow::Error> for ApiError {
    fn from(error: anyhow::Error) -> Self {
        tracing::error!(error = ?error, "storage failure");
        Self::new(StatusCode::INTERNAL_SERVER_ERROR, "internal server error")
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.status, Json(json!({ "detail": self.detail }))).into_response()
    }
}

pub type ApiResult<T> = Result<T, ApiError>;
