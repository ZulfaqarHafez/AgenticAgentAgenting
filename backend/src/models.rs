//! Domain and API models. These mirror the JSON contract the frontend expects.

use chrono::{DateTime, Utc};
use indexmap::IndexMap;
use serde::{Deserialize, Serialize};
use utoipa::ToSchema;
use uuid::Uuid;

use crate::validation::{Validate, Violations};

pub fn utc_now() -> DateTime<Utc> {
    Utc::now()
}

/// Builds ids like `G-3f9a1c2b7d`: a prefix plus the first `len` hex chars of a v4 uuid.
fn prefixed_id(prefix: &str, len: usize) -> String {
    let hex = Uuid::new_v4().simple().to_string();
    format!("{prefix}-{}", &hex[..len])
}

/// Rounds to 3 decimal places, like Python's `round(x, 3)`.
pub fn round3(value: f64) -> f64 {
    (value * 1000.0).round() / 1000.0
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum GoalPriority {
    Low,
    #[default]
    Medium,
    High,
    Critical,
}

impl GoalPriority {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Low => "low",
            Self::Medium => "medium",
            Self::High => "high",
            Self::Critical => "critical",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum GoalStatus {
    #[default]
    Active,
    Completed,
    Blocked,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum RunStatus {
    #[default]
    Active,
    Completed,
    Halted,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum RunMode {
    Lite,
    #[default]
    Balanced,
    Power,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum SpecialistRole {
    Research,
    Planner,
    Executor,
    Critic,
    Verifier,
}

impl SpecialistRole {
    /// Every role, in declaration order.
    pub const ALL: [SpecialistRole; 5] = [
        Self::Research,
        Self::Planner,
        Self::Executor,
        Self::Critic,
        Self::Verifier,
    ];

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Research => "research",
            Self::Planner => "planner",
            Self::Executor => "executor",
            Self::Critic => "critic",
            Self::Verifier => "verifier",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum TurnOutcome {
    Contributed,
    Passed,
    AutoSkipped,
    PriorityPreempted,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum DecisionEventType {
    RoleActivation,
    FallbackTransition,
    ConfidenceShift,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum ProofGateState {
    Ready,
    Blocked,
}

/// Which safety layer the run is operating under.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, ToSchema)]
pub enum FallbackLayer {
    #[serde(rename = "layer_1_circle_junction")]
    CircleJunction,
    #[serde(rename = "layer_2_verifier_guard")]
    VerifierGuard,
    #[serde(rename = "layer_3_safe_baseline")]
    SafeBaseline,
}

fn new_subgoal_id() -> String {
    prefixed_id("SG", 8)
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct Subgoal {
    #[serde(default = "new_subgoal_id")]
    pub id: String,
    pub title: String,
    #[serde(default)]
    pub done: bool,
    #[serde(default)]
    pub confidence: f64,
    #[serde(default)]
    pub evidence_count: i64,
    #[serde(default)]
    pub blocking_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct GoalCreateRequest {
    pub title: String,
    pub success_criteria: Vec<String>,
    #[serde(default)]
    pub constraints: Vec<String>,
    #[serde(default)]
    pub priority: GoalPriority,
    #[serde(default)]
    pub subgoals: Vec<Subgoal>,
}

impl Validate for GoalCreateRequest {
    fn validate(&self, v: &mut Violations) {
        v.text_length(&["title"], &self.title, 3, 240);
        v.check(
            !self.success_criteria.is_empty(),
            &["success_criteria"],
            "List should have at least 1 item after validation, not 0",
        );
        for subgoal in &self.subgoals {
            v.unit_interval(&["subgoals", "confidence"], subgoal.confidence);
        }
    }
}

fn new_goal_id() -> String {
    prefixed_id("G", 10)
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct Goal {
    #[serde(default = "new_goal_id")]
    pub goal_id: String,
    pub title: String,
    pub success_criteria: Vec<String>,
    pub constraints: Vec<String>,
    pub priority: GoalPriority,
    #[serde(default)]
    pub status: GoalStatus,
    #[serde(default)]
    pub subgoals: Vec<Subgoal>,
    #[serde(default = "utc_now")]
    pub created_at: DateTime<Utc>,
    #[serde(default = "utc_now")]
    pub updated_at: DateTime<Utc>,
}

impl From<GoalCreateRequest> for Goal {
    fn from(request: GoalCreateRequest) -> Self {
        let now = utc_now();
        Goal {
            goal_id: new_goal_id(),
            title: request.title,
            success_criteria: request.success_criteria,
            constraints: request.constraints,
            priority: request.priority,
            status: GoalStatus::Active,
            subgoals: request.subgoals,
            created_at: now,
            updated_at: now,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
#[serde(default)]
pub struct RunStartRequest {
    pub run_mode: RunMode,
    pub active_roles: Option<Vec<SpecialistRole>>,
    pub include_roles: Option<Vec<SpecialistRole>>,
    pub auto_role_limit: usize,
    pub min_usefulness: f64,
    pub max_low_value_streak: u32,
    pub enable_priority_preemption: bool,
}

impl Default for RunStartRequest {
    fn default() -> Self {
        Self {
            run_mode: RunMode::Balanced,
            active_roles: None,
            include_roles: None,
            auto_role_limit: 3,
            min_usefulness: 0.35,
            max_low_value_streak: 2,
            enable_priority_preemption: true,
        }
    }
}

impl Validate for RunStartRequest {
    fn validate(&self, v: &mut Violations) {
        v.int_range(&["auto_role_limit"], self.auto_role_limit as i64, 1, 5);
        v.unit_interval(&["min_usefulness"], self.min_usefulness);
        v.int_range(
            &["max_low_value_streak"],
            self.max_low_value_streak as i64,
            1,
            10,
        );
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct TurnInput {
    pub role: SpecialistRole,
    #[serde(default)]
    pub user_prompt: String,
    #[serde(default)]
    pub contribution: String,
    #[serde(default)]
    pub confidence: f64,
    #[serde(default)]
    pub evidence_refs: Vec<String>,
    #[serde(default)]
    pub usefulness_score: f64,
    #[serde(default)]
    pub pass_turn: bool,
    #[serde(default)]
    pub requested_next_role: Option<SpecialistRole>,
    #[serde(default)]
    pub priority_override: bool,
    #[serde(default)]
    pub specialist_output: Option<SpecialistOutput>,
}

impl TurnInput {
    /// A contributing turn with everything else defaulted. Handy in tests.
    pub fn contribution(
        role: SpecialistRole,
        contribution: &str,
        confidence: f64,
        usefulness_score: f64,
    ) -> Self {
        Self {
            role,
            user_prompt: String::new(),
            contribution: contribution.to_string(),
            confidence,
            evidence_refs: Vec::new(),
            usefulness_score,
            pass_turn: false,
            requested_next_role: None,
            priority_override: false,
            specialist_output: None,
        }
    }
}

impl Validate for TurnInput {
    fn validate(&self, v: &mut Violations) {
        v.unit_interval(&["confidence"], self.confidence);
        v.unit_interval(&["usefulness_score"], self.usefulness_score);
        let has_contribution = !self.contribution.trim().is_empty();
        v.check(
            self.pass_turn || has_contribution,
            &[],
            "Value error, contribution is required when pass_turn is false",
        );
        v.check(
            !(self.pass_turn && has_contribution),
            &[],
            "Value error, contribution must be empty when pass_turn is true",
        );
    }
}

fn default_provider() -> String {
    "prompted_local_engine".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct SpecialistOutput {
    pub role: SpecialistRole,
    #[serde(default = "default_provider")]
    pub provider: String,
    pub prompt_title: String,
    pub system_prompt: String,
    pub message: String,
    #[serde(default)]
    pub checklist: Vec<String>,
    #[serde(default)]
    pub evidence_notes: Vec<String>,
    #[serde(default)]
    pub suggested_next_role: Option<SpecialistRole>,
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct TurnRecord {
    pub turn_number: u32,
    pub round_number: u32,
    pub role: SpecialistRole,
    #[serde(default)]
    pub user_prompt: String,
    pub outcome: TurnOutcome,
    pub confidence: f64,
    pub confidence_delta_from_previous_turn: f64,
    pub usefulness_score: f64,
    pub evidence_refs: Vec<String>,
    pub contribution: String,
    #[serde(default)]
    pub specialist_output: Option<SpecialistOutput>,
    pub role_activation_reason: String,
    pub requested_next_role: Option<SpecialistRole>,
    pub next_role: SpecialistRole,
    pub next_role_activation_reason: String,
    pub reason: String,
    pub fallback_layer_before: FallbackLayer,
    pub fallback_layer_after: FallbackLayer,
    pub fallback_transitioned: bool,
    #[serde(default = "utc_now")]
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct ProofGateStatus {
    pub state: ProofGateState,
    pub ready_to_complete: bool,
    pub min_turns_required: u32,
    pub turns_observed: u32,
    pub evidence_refs_required: u32,
    pub evidence_refs_observed: u32,
    pub verifier_turn_required: bool,
    pub verifier_turn_observed: bool,
    pub minimum_average_confidence: f64,
    pub observed_average_confidence: f64,
    #[serde(default)]
    pub blockers: Vec<String>,
    #[serde(default)]
    pub cleared_checks: Vec<String>,
    #[serde(default = "utc_now")]
    pub last_evaluated_at: DateTime<Utc>,
}

impl Default for ProofGateStatus {
    fn default() -> Self {
        Self {
            state: ProofGateState::Blocked,
            ready_to_complete: false,
            min_turns_required: 3,
            turns_observed: 0,
            evidence_refs_required: 2,
            evidence_refs_observed: 0,
            verifier_turn_required: true,
            verifier_turn_observed: false,
            minimum_average_confidence: 0.68,
            observed_average_confidence: 0.0,
            blockers: vec![
                "Run needs more specialist turns before it can be completed.".to_string(),
                "Evidence markers have not met the minimum threshold yet.".to_string(),
                "Verifier review has not been recorded yet.".to_string(),
            ],
            cleared_checks: Vec::new(),
            last_evaluated_at: utc_now(),
        }
    }
}

fn new_run_id() -> String {
    prefixed_id("R", 10)
}

fn default_activation_strategy() -> String {
    "manual_active_roles".to_string()
}

fn default_activation_reason() -> String {
    "run started with first configured specialist in rotation".to_string()
}

fn one() -> u32 {
    1
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct Run {
    #[serde(default = "new_run_id")]
    pub run_id: String,
    pub goal_id: String,
    #[serde(default)]
    pub run_mode: RunMode,
    pub active_roles: Vec<SpecialistRole>,
    #[serde(default = "default_activation_strategy")]
    pub activation_strategy: String,
    #[serde(default)]
    pub activation_recommendations: Vec<SkillRecommendation>,
    #[serde(default)]
    pub current_index: usize,
    pub current_role: SpecialistRole,
    #[serde(default = "default_activation_reason")]
    pub current_role_activation_reason: String,
    #[serde(default = "one")]
    pub round_number: u32,
    #[serde(default)]
    pub turn_number: u32,
    #[serde(default)]
    pub round_passes: Vec<SpecialistRole>,
    pub low_value_streaks: IndexMap<SpecialistRole, u32>,
    #[serde(default)]
    pub paused_roles: Vec<SpecialistRole>,
    #[serde(default)]
    pub status: RunStatus,
    #[serde(default)]
    pub turn_history: Vec<TurnRecord>,
    #[serde(default)]
    pub proof_gate_status: ProofGateStatus,
    pub min_usefulness: f64,
    pub max_low_value_streak: u32,
    pub enable_priority_preemption: bool,
    #[serde(default = "utc_now")]
    pub created_at: DateTime<Utc>,
    #[serde(default = "utc_now")]
    pub updated_at: DateTime<Utc>,
}

impl Run {
    /// A fresh run with defaults for everything not given.
    pub fn new(
        goal_id: &str,
        request: &RunStartRequest,
        active_roles: Vec<SpecialistRole>,
    ) -> Self {
        let now = utc_now();
        Self {
            run_id: new_run_id(),
            goal_id: goal_id.to_string(),
            run_mode: request.run_mode,
            current_role: active_roles[0],
            low_value_streaks: active_roles.iter().map(|role| (*role, 0)).collect(),
            active_roles,
            activation_strategy: default_activation_strategy(),
            activation_recommendations: Vec::new(),
            current_index: 0,
            current_role_activation_reason: default_activation_reason(),
            round_number: 1,
            turn_number: 0,
            round_passes: Vec::new(),
            paused_roles: Vec::new(),
            status: RunStatus::Active,
            turn_history: Vec::new(),
            proof_gate_status: ProofGateStatus::default(),
            min_usefulness: request.min_usefulness,
            max_low_value_streak: request.max_low_value_streak,
            enable_priority_preemption: request.enable_priority_preemption,
            created_at: now,
            updated_at: now,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct RunReport {
    pub run_id: String,
    pub goal_id: String,
    pub status: RunStatus,
    pub turns: u32,
    pub rounds: u32,
    pub activated_roles: Vec<SpecialistRole>,
    pub role_turn_counts: IndexMap<SpecialistRole, u32>,
    pub role_pass_counts: IndexMap<SpecialistRole, u32>,
    pub role_avg_usefulness: IndexMap<SpecialistRole, f64>,
    pub paused_roles: Vec<SpecialistRole>,
    pub fallback_layer: FallbackLayer,
    pub proof_gate_status: ProofGateStatus,
}

pub fn new_event_id() -> String {
    prefixed_id("E", 10)
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct DecisionLedgerEntry {
    pub event_id: String,
    pub run_id: String,
    pub turn_number: u32,
    pub round_number: u32,
    pub event_type: DecisionEventType,
    pub role: Option<SpecialistRole>,
    pub activated_role: Option<SpecialistRole>,
    pub reason: String,
    pub confidence_before: Option<f64>,
    pub confidence_after: Option<f64>,
    pub confidence_delta: Option<f64>,
    pub fallback_from: Option<FallbackLayer>,
    pub fallback_to: Option<FallbackLayer>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct SkillRecommendationRequest {
    pub goal_title: String,
    #[serde(default)]
    pub success_criteria: Vec<String>,
    #[serde(default)]
    pub constraints: Vec<String>,
    #[serde(default)]
    pub include_roles: Option<Vec<SpecialistRole>>,
    #[serde(default = "default_recommendation_limit")]
    pub limit: usize,
}

fn default_recommendation_limit() -> usize {
    5
}

impl Validate for SkillRecommendationRequest {
    fn validate(&self, v: &mut Violations) {
        v.text_length(&["goal_title"], &self.goal_title, 3, 240);
        v.int_range(&["limit"], self.limit as i64, 1, 5);
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct SkillRecommendation {
    pub role: SpecialistRole,
    pub activation_score: f64,
    pub expected_utility: f64,
    pub cost_penalty: f64,
    pub latency_penalty: f64,
    pub risk_reduction: f64,
    pub rationale: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct AutoTurnRequest {
    pub user_prompt: String,
    #[serde(default)]
    pub priority_override: bool,
}

impl Validate for AutoTurnRequest {
    fn validate(&self, v: &mut Violations) {
        v.text_length(&["user_prompt"], &self.user_prompt, 3, 4000);
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct HealthResponse {
    pub status: String,
    pub service: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct RuntimeStatusResponse {
    pub status: String,
    pub service: String,
    pub api_version: String,
    pub contract_version: String,
    pub recommended_roles_supported: bool,
    pub decision_ledger_supported: bool,
    pub store_backend: String,
    pub server_started_at: DateTime<Utc>,
    pub server_now: DateTime<Utc>,
    pub uptime_seconds: f64,
    pub total_runs: usize,
    pub active_runs: usize,
}
