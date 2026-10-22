//! Request body parsing and field validation.
//!
//! Errors come back as 422 with a FastAPI-style list:
//! `{"detail": [{"type": ..., "loc": ["body", field], "msg": ...}]}`.

use axum::body::Bytes;
use axum::extract::{FromRequest, Request};
use serde::de::DeserializeOwned;
use serde_json::{Value, json};

use crate::error::ApiError;

/// Collects field-level problems found while validating a request.
#[derive(Debug, Default)]
pub struct Violations(Vec<Value>);

impl Violations {
    pub fn check(&mut self, ok: bool, field: &[&str], message: impl Into<String>) {
        if !ok {
            let mut loc = vec![Value::from("body")];
            loc.extend(field.iter().map(|part| Value::from(*part)));
            self.0
                .push(json!({ "type": "value_error", "loc": loc, "msg": message.into() }));
        }
    }

    /// Length in characters must be within `min..=max`.
    pub fn text_length(&mut self, field: &[&str], value: &str, min: usize, max: usize) {
        let length = value.chars().count();
        self.check(
            length >= min,
            field,
            format!("String should have at least {min} characters"),
        );
        self.check(
            length <= max,
            field,
            format!("String should have at most {max} characters"),
        );
    }

    pub fn int_range(&mut self, field: &[&str], value: i64, min: i64, max: i64) {
        self.check(
            value >= min,
            field,
            format!("Input should be greater than or equal to {min}"),
        );
        self.check(
            value <= max,
            field,
            format!("Input should be less than or equal to {max}"),
        );
    }

    /// Value must be within `0.0..=1.0`.
    pub fn unit_interval(&mut self, field: &[&str], value: f64) {
        self.check(
            value >= 0.0,
            field,
            "Input should be greater than or equal to 0",
        );
        self.check(
            value <= 1.0,
            field,
            "Input should be less than or equal to 1",
        );
    }

    pub fn into_result(self) -> Result<(), ApiError> {
        if self.0.is_empty() {
            Ok(())
        } else {
            Err(ApiError::unprocessable(Value::Array(self.0)))
        }
    }
}

/// Field rules that serde alone can't express (lengths, ranges, cross-field checks).
pub trait Validate {
    fn validate(&self, violations: &mut Violations);
}

fn parse_body<T: DeserializeOwned + Validate>(bytes: &[u8]) -> Result<T, ApiError> {
    let value: T = serde_json::from_slice(bytes).map_err(|error| {
        let kind = if error.is_syntax() || error.is_eof() {
            "json_invalid"
        } else {
            "value_error"
        };
        ApiError::unprocessable(
            json!([{ "type": kind, "loc": ["body"], "msg": error.to_string() }]),
        )
    })?;
    let mut violations = Violations::default();
    value.validate(&mut violations);
    violations.into_result()?;
    Ok(value)
}

async fn read_body<S: Send + Sync>(req: Request, state: &S) -> Result<Bytes, ApiError> {
    Bytes::from_request(req, state)
        .await
        .map_err(|rejection| ApiError::new(rejection.status(), rejection.body_text()))
}

/// A JSON body that must be present and valid.
pub struct ValidJson<T>(pub T);

impl<S, T> FromRequest<S> for ValidJson<T>
where
    S: Send + Sync,
    T: DeserializeOwned + Validate,
{
    type Rejection = ApiError;

    async fn from_request(req: Request, state: &S) -> Result<Self, Self::Rejection> {
        let bytes = read_body(req, state).await?;
        parse_body(&bytes).map(ValidJson)
    }
}

/// A JSON body that may be omitted entirely, in which case `T::default()` is used.
pub struct OptionalJson<T>(pub T);

impl<S, T> FromRequest<S> for OptionalJson<T>
where
    S: Send + Sync,
    T: DeserializeOwned + Validate + Default,
{
    type Rejection = ApiError;

    async fn from_request(req: Request, state: &S) -> Result<Self, Self::Rejection> {
        let bytes = read_body(req, state).await?;
        if bytes.iter().all(u8::is_ascii_whitespace) {
            return Ok(OptionalJson(T::default()));
        }
        parse_body(&bytes).map(OptionalJson)
    }
}
