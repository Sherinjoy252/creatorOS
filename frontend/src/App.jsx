
import { useEffect, useState } from "react";
import "./App.css";

const emptyPosts = ["", "", ""];

const evaluationCriteria = [
  ["technical_accuracy", "Technical accuracy"],
  ["practical_value", "Practical value"],
  ["brand_voice_alignment", "Brand voice alignment"],
  ["readability", "Readability"],
  ["conciseness", "Conciseness"],
  ["topic_relevance", "Topic relevance"],
  ["engagement_potential", "Engagement potential"],
];

function EvaluationPanel({ initialEvaluation, finalEvaluation, scoreDelta }) {
  if (!initialEvaluation && !finalEvaluation) {
    return (
      <section className="evaluation-panel" style={{ marginTop: "1.5rem" }}>
        <h3>Self-evaluation</h3>
        <p className="profile-description">Evaluation details are not available for this post.</p>
      </section>
    );
  }

  const delta = scoreDelta ?? (
    typeof initialEvaluation?.score === "number" && typeof finalEvaluation?.score === "number"
      ? finalEvaluation.score - initialEvaluation.score
      : null
  );

  const renderEvaluation = (evaluation, title) => {
    if (!evaluation) {
      return <p>{title} is not available.</p>;
    }

    return (
      <div className="evaluation-stage" style={{ marginTop: "1rem" }}>
        <h4>{title}: {evaluation.score ?? "—"}/100</h4>
        <div style={{ display: "grid", gap: "0.85rem" }}>
          {evaluationCriteria.map(([key, label]) => {
            const criterion = evaluation.criteria?.[key];
            if (!criterion) return null;
            const maxScore = criterion.max_score ?? 0;
            const score = criterion.score ?? 0;
            const percentage = maxScore > 0 ? Math.max(0, Math.min(100, (score / maxScore) * 100)) : 0;

            return (
              <div key={`${title}-${key}`} className="evaluation-criterion">
                <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "baseline" }}>
                  <strong>{label}</strong>
                  <span>{score}/{maxScore}</span>
                </div>
                <div style={{ height: "7px", background: "#e8ebf0", borderRadius: "999px", overflow: "hidden", margin: "0.35rem 0" }}>
                  <div style={{ width: `${percentage}%`, height: "100%", background: "#4263a5", borderRadius: "999px" }} />
                </div>
                {criterion.feedback && <p className="profile-description" style={{ margin: 0 }}>{criterion.feedback}</p>}
              </div>
            );
          })}
        </div>
        {evaluation.summary && <p style={{ marginTop: "1rem" }}><strong>Summary:</strong> {evaluation.summary}</p>}
        {evaluation.strengths?.length > 0 && (
          <div><strong>Strengths</strong><ul>{evaluation.strengths.map((item, index) => <li key={index}>{item}</li>)}</ul></div>
        )}
        {evaluation.improvements?.length > 0 && (
          <div><strong>Areas to improve</strong><ul>{evaluation.improvements.map((item, index) => <li key={index}>{item}</li>)}</ul></div>
        )}
      </div>
    );
  };

  return (
    <section className="evaluation-panel" style={{ marginTop: "1.5rem", padding: "1.25rem", border: "1px solid #d7dce5", borderRadius: "12px" }}>
      <h3>Self-evaluation</h3>
      <p className="profile-description">An independent assessment of the first draft and the final edited version.</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.75rem" }}>
        <div className="history-item"><span>Initial score</span><h3>{initialEvaluation?.score ?? "—"}/100</h3></div>
        <div className="history-item"><span>Final score</span><h3>{finalEvaluation?.score ?? "—"}/100</h3></div>
        <div className="history-item"><span>Score change</span><h3>{delta === null ? "—" : `${delta > 0 ? "+" : ""}${delta} points`}</h3></div>
      </div>
      {renderEvaluation(initialEvaluation, "Initial evaluation")}
      <div style={{ borderTop: "1px solid #d7dce5", marginTop: "1.25rem", paddingTop: "0.25rem" }}>
        {renderEvaluation(finalEvaluation, "Final evaluation")}
      </div>
    </section>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [posts, setPosts] = useState(emptyPosts);
  const [profile, setProfile] = useState("");
  const [hasProfile, setHasProfile] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [savingMessage, setSavingMessage] = useState("");
  const [topic, setTopic] = useState("");
  const [generatedContent, setGeneratedContent] = useState(null);
  const [contentGenerating, setContentGenerating] = useState(false);
  const [contentHistory, setContentHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState(null);
  const [performanceHistory, setPerformanceHistory] = useState([]);
  const [audienceComments, setAudienceComments] = useState("");
  const [performanceForm, setPerformanceForm] = useState({
    impressions: "",
    likes: "",
    comments: "",
    reposts: "",
  });
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [performanceSaving, setPerformanceSaving] = useState(false);
  const [performanceMessage, setPerformanceMessage] = useState("");
  const [learningLessons, setLearningLessons] = useState([]);
  const [lessonsLoading, setLessonsLoading] = useState(false);
  const [lessonActionId, setLessonActionId] = useState("");

  async function loadUser() {
    try {
      const response = await fetch("/auth/me", {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.user ?? data);
      } else {
        setUser(null);
      }
    } catch {
      setError("Unable to connect to CreatorOS. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  async function loadBrandVoice() {
    try {
      const response = await fetch("/api/brand-voice", {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setProfile(data.profile);
        setPosts(data.sample_posts);
        setHasProfile(true);
      } else if (response.status === 404) {
        setHasProfile(false);
        setProfile("");
        setPosts(emptyPosts);
      } else if (response.status === 401) {
        setError("Your session has expired. Please sign in again.");
      } else {
        setError("Unable to load your brand voice.");
      }
    } catch {
      setError("Unable to connect to CreatorOS.");
    }
  }

  useEffect(() => {
    loadUser();
  }, []);

  useEffect(() => {
    if (user) {
      loadBrandVoice();
      loadContentHistory();
    }
  }, [user]);

  function handleLogin() {
    window.location.href = "/auth/linkedin/login";
  }

  async function handleLogout() {
    setError("");

    try {
      const response = await fetch("/auth/logout", {
        method: "POST",
        credentials: "include",
      });

      if (response.ok) {
        setUser(null);
        setProfile("");
        setPosts(emptyPosts);
        setHasProfile(false);
        setTopic("");
        setGeneratedContent(null);
        setContentHistory([]);
        setSelectedHistoryItem(null);
        setPerformanceHistory([]);
        setLearningLessons([]);
        setAudienceComments("");
        setPerformanceForm({
          impressions: "",
          likes: "",
          comments: "",
          reposts: "",
        });
        setPerformanceMessage("");
        setSavingMessage("");
      } else {
        setError("Logout failed. Please try again.");
      }
    } catch {
      setError("Unable to connect to CreatorOS.");
    }
  }

  function updatePost(index, value) {
    setPosts((current) =>
      current.map((post, i) => (i === index ? value : post))
    );
  }

  function addPost() {
    if (posts.length < 10) {
      setPosts((current) => [...current, ""]);
    }
  }

  function removePost(index) {
    if (posts.length > 3) {
      setPosts((current) => current.filter((_, i) => i !== index));
    }
  }

  async function handleGenerate(event) {
    event.preventDefault();
    setError("");
    setSavingMessage("");

    const validPosts = posts.map((post) => post.trim()).filter(Boolean);

    if (validPosts.length < 3) {
      setError("Please enter at least 3 non-empty sample posts.");
      return;
    }

    setGenerating(true);

    try {
      const response = await fetch("/api/brand-voice", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ sample_posts: validPosts }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || "Unable to generate your brand voice.");
        return;
      }

      setProfile(data.profile);
      setPosts(data.sample_posts);
      setHasProfile(true);
      setSavingMessage("Your brand voice has been generated and saved.");
    } catch {
      setError("Unable to connect to CreatorOS.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleGenerateContent(event) {
    event.preventDefault();
    setError("");
    setGeneratedContent(null);

    if (topic.trim().length < 3) {
      setError("Please enter a topic with at least 3 characters.");
      return;
    }

    setContentGenerating(true);

    try {
      const response = await fetch("/api/content/generate", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic: topic.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to generate content. Please try again."
        );
        return;
      }

      setGeneratedContent(data);
      await loadContentHistory();
    } catch {
      setError("Unable to connect to CreatorOS. Please try again.");
    } finally {
      setContentGenerating(false);
    }
  }

  async function loadLearningLessons(contentId) {
    setLessonsLoading(true);
    try {
      const response = await fetch(
        `/api/content/${contentId}/lessons`,
        { credentials: "include" }
      );
      const data = await response.json();

      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to load learning lessons."
        );
        return;
      }

      setLearningLessons(data);
    } catch {
      setError("Unable to connect while loading learning lessons.");
    } finally {
      setLessonsLoading(false);
    }
  }

  async function handleLessonDecision(lessonId, decision) {
    if (!selectedHistoryItem) return;

    setError("");
    setLessonActionId(lessonId);

    try {
      const response = await fetch(
        `/api/content/${selectedHistoryItem.id}/lessons/${lessonId}/${decision}`,
        {
          method: "POST",
          credentials: "include",
        }
      );
      const data = await response.json();

      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : `Unable to ${decision} lesson.`
        );
        return;
      }

      // Update only the selected lesson. Do not trigger a new analysis.
      setLearningLessons((current) =>
        current.map((lesson) =>
          lesson.id === lessonId
            ? {
                ...lesson,
                status: data.status,
                approved_at: data.approved_at ?? null,
              }
            : lesson
        )
      );
    } catch {
      setError("Unable to connect while updating the lesson.");
    } finally {
      setLessonActionId("");
    }
  }

  async function handleSelectHistoryItem(item) {
    if (selectedHistoryItem?.id === item.id) {
      setSelectedHistoryItem(null);
      setLearningLessons([]);
      return;
    }

    setSelectedHistoryItem(item);
    setLearningLessons([]);
    loadLearningLessons(item.id);
    setPerformanceHistory([]);
    setPerformanceMessage("");
    setError("");
    setPerformanceLoading(true);

    try {
      const response = await fetch(
        `/api/content/${item.id}/performance`,
        { credentials: "include" }
      );
      const data = await response.json();

      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to load performance history."
        );
        return;
      }

      setPerformanceHistory(data);
      const latest = data.length > 0 ? data[data.length - 1] : null;
      if (latest) {
        setPerformanceForm({
          impressions: String(latest.impressions),
          likes: String(latest.likes),
          comments: String(latest.comments),
          reposts: String(latest.reposts),
        });
        setAudienceComments((latest.audience_comments || []).join("\\n"));
      } else {
        setAudienceComments("");
        setPerformanceForm({
          impressions: "",
          likes: "",
          comments: "",
          reposts: "",
        });
      }
    } catch {
      setError("Unable to connect to CreatorOS while loading performance.");
    } finally {
      setPerformanceLoading(false);
    }
  }

  function updatePerformanceField(field, value) {
    setPerformanceForm((current) => ({ ...current, [field]: value }));
  }

  async function submitPerformance(values, dataSource = "manual") {
    if (!selectedHistoryItem) return;

    setError("");
    setPerformanceMessage("");
    setPerformanceSaving(true);

    try {
      const response = await fetch(
        `/api/content/${selectedHistoryItem.id}/performance`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            impressions: Number(values.impressions),
            likes: Number(values.likes),
            comments: Number(values.comments),
            reposts: Number(values.reposts),
            audience_comments:
              dataSource === "manual"
                ? audienceComments
                    .split("\\n")
                    .map((comment) => comment.trim())
                    .filter(Boolean)
                : [],
            data_source: dataSource,
          }),
        }
      );

      const data = await response.json();
      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to save performance metrics."
        );
        return;
      }

      setPerformanceHistory((current) => [...current, data]);
      await loadLearningLessons(selectedHistoryItem.id);
      setPerformanceForm({
        impressions: String(data.impressions),
        likes: String(data.likes),
        comments: String(data.comments),
        reposts: String(data.reposts),
      });
      setPerformanceMessage(
        dataSource === "simulated"
          ? "Simulated performance snapshot saved."
          : "Performance snapshot saved."
      );
    } catch {
      setError("Unable to connect to CreatorOS while saving performance.");
    } finally {
      setPerformanceSaving(false);
    }
  }

  async function handleSavePerformance(event) {
    event.preventDefault();

    const fields = ["impressions", "likes", "comments", "reposts"];
    const hasInvalidValue = fields.some((field) => {
      const value = performanceForm[field];
      return value === "" || !Number.isInteger(Number(value)) || Number(value) < 0;
    });

    if (hasInvalidValue) {
      setError("Enter whole numbers greater than or equal to zero for every metric.");
      return;
    }

    await submitPerformance(performanceForm, "manual");
  }

  async function handleSimulatePerformance() {
    const latest =
      performanceHistory.length > 0
        ? performanceHistory[performanceHistory.length - 1]
        : { impressions: 0, likes: 0, comments: 0, reposts: 0 };

    // Demo-only increments: these are sample values, not LinkedIn analytics.
    const simulatedValues = {
      impressions: latest.impressions + Math.max(50, Math.round(latest.impressions * 0.25)),
      likes: latest.likes + Math.max(2, Math.round(latest.likes * 0.15)),
      comments: latest.comments + (latest.comments % 2 === 0 ? 1 : 0),
      reposts: latest.reposts + (latest.reposts % 3 === 0 ? 1 : 0),
    };

    await submitPerformance(simulatedValues, "simulated");
  }

  async function loadContentHistory() {
    setHistoryLoading(true);

    try {
      const response = await fetch("/api/content/history", {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setContentHistory(data);
      } else if (response.status === 401) {
        setError("Your session has expired. Please sign in again.");
      } else {
        setError("Unable to load content history.");
      }
    } catch {
      setError("Unable to connect to CreatorOS.");
    } finally {
      setHistoryLoading(false);
    }
  }

  if (loading) {
    return (
      <main className="login-page">
        <p>Loading CreatorOS...</p>
      </main>
    );
  }

  if (user) {
    return (
      <main className="login-page">
        <nav className="navbar">
          <div className="brand">
            <span className="brand-icon">C</span>
            <span>CreatorOS</span>
          </div>

          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </nav>

        <section className="hero studio">
          <div className="hero-badge">
            <span className="status-dot" />
            Your workspace
          </div>

          <h1>
            Welcome back,
            <br />
            <span>{user.name || "Creator"}.</span>
          </h1>

          <p className="subtitle">
            Let's teach CreatorOS how you write, using your existing LinkedIn
            posts.
          </p>

          <form className="brand-voice-form" onSubmit={handleGenerate}>
            <h2>
              {hasProfile ? "Update your brand voice" : "Build your brand voice"}
            </h2>

            <p>
              Paste 3–10 of your existing posts. We'll analyze your writing
              style and save a reusable profile for future content.
            </p>

            {posts.map((post, index) => (
              <div className="post-input" key={index}>
                <label htmlFor={`sample-post-${index}`}>
                  Sample post {index + 1}
                </label>

                <textarea
                  id={`sample-post-${index}`}
                  value={post}
                  onChange={(event) => updatePost(index, event.target.value)}
                  placeholder="Paste one of your LinkedIn posts here..."
                  rows={4}
                  required={index < 3}
                />

                {posts.length > 3 && (
                  <button
                    type="button"
                    className="remove-post-button"
                    onClick={() => removePost(index)}
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}

            {posts.length < 10 && (
              <button
                type="button"
                className="secondary-button"
                onClick={addPost}
              >
                + Add another post
              </button>
            )}

            <button
              type="submit"
              className="linkedin-button generate-button"
              disabled={generating}
            >
              {generating
                ? "Analyzing your writing..."
                : hasProfile
                  ? "Regenerate brand voice"
                  : "Generate my brand voice"}
            </button>
          </form>

          {error && <p className="error-message">{error}</p>}

          {savingMessage && (
            <p className="success-message">{savingMessage}</p>
          )}

          {profile && (
            <section className="profile-panel">
              <h2>Your brand voice profile</h2>

              <p className="profile-description">
                This profile will guide CreatorOS when generating your content.
              </p>

              <pre className="profile-content">{profile}</pre>
            </section>
          )}

          {/* Create LinkedIn content */}
          {hasProfile && (
            <section className="profile-panel content-studio">
              <h2>Create LinkedIn content</h2>

              <p className="profile-description">
                Choose a topic. CreatorOS will plan, write, review, and refine
                a post using your saved brand voice.
              </p>

              <form onSubmit={handleGenerateContent}>
                <label htmlFor="content-topic">
                  What do you want to write about?
                </label>

                <textarea
                  id="content-topic"
                  value={topic}
                  onChange={(event) => setTopic(event.target.value)}
                  placeholder="For example: How Spring Boot dependency injection works"
                  rows={3}
                  minLength={3}
                  maxLength={300}
                  required
                />

                <button
                  type="submit"
                  className="linkedin-button generate-button"
                  disabled={contentGenerating}
                >
                  {contentGenerating
                    ? "Creating your post..."
                    : "Generate post"}
                </button>
              </form>

              {generatedContent && (
                <div className="generated-content">
                  <h3>Generated LinkedIn post</h3>

                  <p>
                    Approval status:{" "}
                    <strong>
                      {generatedContent.approved ? "Approved" : "Needs review"}
                    </strong>
                  </p>

                  <p>
                    Revisions:{" "}
                    <strong>{generatedContent.revision_count}</strong>
                  </p>

                  <pre className="profile-content">
                    {generatedContent.draft}
                  </pre>

                  <h3>Strategist's approach</h3>

                  <p>
                    <strong>Angle:</strong>{" "}
                    {generatedContent.strategist_angle}
                  </p>

                  <p>
                    <strong>Reason:</strong>{" "}
                    {generatedContent.strategy_reason}
                  </p>

                  <h3>Agent audit trail</h3>

                  <ol>
                    {generatedContent.audit_trail?.map((entry, index) => (
                      <li key={index}>{entry}</li>
                    ))}
                  </ol>

                  <EvaluationPanel
                    initialEvaluation={generatedContent.initial_evaluation}
                    finalEvaluation={generatedContent.final_evaluation}
                    scoreDelta={generatedContent.evaluation_score_delta}
                  />
                </div>
              )}
            </section>
          )}

          {/* Content History: each selected post expands directly in its own card. */}
          <section className="profile-panel content-studio">
            <h2>Content History</h2>

            {historyLoading && <p>Loading saved posts...</p>}

            {!historyLoading && contentHistory.length === 0 && (
              <p>No saved posts yet. Generate your first post above.</p>
            )}

            <div className="content-history-list">
              {contentHistory.map((item) => {
                const isExpanded = selectedHistoryItem?.id === item.id;

                return (
                  <article key={item.id} className="history-item">
                    <h3>{item.topic}</h3>

                    <p>
                      Status: {item.approved ? "Approved" : "Needs review"}
                      {" · "}
                      Revisions: {item.revision_count}
                    </p>

                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => handleSelectHistoryItem(item)}
                    >
                      {isExpanded ? "Hide post" : "View post"}
                    </button>

                    {isExpanded && (
                      <div className="generated-content expanded-post">
                        <h3>Generated post</h3>

                        <p>
                          Approval status:{" "}
                          <strong>
                            {selectedHistoryItem.approved ? "Approved" : "Needs review"}
                          </strong>
                        </p>

                        <pre className="profile-content">
                          {selectedHistoryItem.draft}
                        </pre>

                        <h4>Strategist's approach</h4>
                        <p>
                          <strong>Angle:</strong>{" "}
                          {selectedHistoryItem.strategist_angle}
                        </p>
                        <p>{selectedHistoryItem.strategy_reason}</p>

                        <h4>Audit trail</h4>
                        <ol>
                          {selectedHistoryItem.audit_trail?.map((entry, index) => (
                            <li key={index}>{entry}</li>
                          ))}
                        </ol>

                        <EvaluationPanel
                          initialEvaluation={selectedHistoryItem.initial_evaluation}
                          finalEvaluation={selectedHistoryItem.final_evaluation}
                          scoreDelta={selectedHistoryItem.evaluation_score_delta}
                        />

                        <section
                          className="performance-panel"
                          style={{
                            marginTop: "1.5rem",
                            paddingTop: "1.5rem",
                            borderTop: "1px solid #d7dce5",
                          }}
                        >
                          <h3>Performance tracking</h3>
                          <p className="profile-description">
                            Enter the latest LinkedIn metrics or create clearly labelled
                            simulated data. Every save creates a separate snapshot.
                          </p>

                          {performanceLoading && <p>Loading performance history...</p>}

                          <form onSubmit={handleSavePerformance}>
                            <div
                              className="performance-fields"
                              style={{
                                display: "grid",
                                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                                gap: "1rem",
                              }}
                            >
                              {[
                                ["impressions", "Impressions"],
                                ["likes", "Likes"],
                                ["comments", "Comments"],
                                ["reposts", "Reposts"],
                              ].map(([field, label]) => (
                                <div className="post-input" key={field}>
                                  <label htmlFor={`performance-${field}`}>{label}</label>
                                  <input
                                    id={`performance-${field}`}
                                    type="number"
                                    min="0"
                                    step="1"
                                    required
                                    value={performanceForm[field]}
                                    onChange={(event) =>
                                      updatePerformanceField(field, event.target.value)
                                    }
                                  />
                                </div>
                              ))}
                            </div>

                            <div className="post-input" style={{ marginTop: "1rem" }}>
                              <label htmlFor="audience-comments">
                                Audience comments (optional)
                              </label>
                              <textarea
                                id="audience-comments"
                                value={audienceComments}
                                onChange={(event) => setAudienceComments(event.target.value)}
                                placeholder={"Paste LinkedIn comments here, one comment per line...\\n\\nThis was really helpful!\\nCould you share a practical example?"}
                                rows={6}
                              />
                              <p className="helper-text">
                                Paste actual LinkedIn comments, one per line. Comments
                                are included only with manual performance snapshots.
                              </p>
                            </div>

                            <div
                              className="performance-actions"
                              style={{
                                display: "flex",
                                flexWrap: "wrap",
                                gap: "0.75rem",
                                marginTop: "1rem",
                              }}
                            >
                              <button
                                type="submit"
                                className="linkedin-button generate-button"
                                disabled={performanceSaving || performanceLoading}
                              >
                                {performanceSaving ? "Saving..." : "Save manual metrics"}
                              </button>
                              <button
                                type="button"
                                className="secondary-button"
                                onClick={handleSimulatePerformance}
                                disabled={performanceSaving || performanceLoading}
                              >
                                Simulate next update
                              </button>
                            </div>
                          </form>

                          {performanceMessage && (
                            <p className="success-message">{performanceMessage}</p>
                          )}

                          <h4>Snapshot history</h4>
                          {performanceHistory.length === 0 && !performanceLoading ? (
                            <p>No performance snapshots yet.</p>
                          ) : (
                            <div className="performance-history">
                              {performanceHistory.map((snapshot) => (
                                <article className="history-item" key={snapshot.id}>
                                  <p>
                                    <strong>
                                      {snapshot.data_source === "simulated"
                                        ? "Simulated data"
                                        : "Manual data"}
                                    </strong>
                                    {" · "}
                                    {snapshot.recorded_at
                                      ? new Date(snapshot.recorded_at).toLocaleString()
                                      : "Recently saved"}
                                  </p>
                                  <p>
                                    Impressions: {snapshot.impressions} · Likes: {snapshot.likes}
                                    {" · "}Comments: {snapshot.comments} · Reposts: {snapshot.reposts}
                                  </p>
                                </article>
                              ))}
                            </div>
                          )}

                          <h4>Learning lessons for this post</h4>
                          <p className="profile-description">
                            Review the suggestions generated from this post's performance.
                            Approving a lesson saves that decision; it does not run another analysis.
                            Only approved lessons are used in future content generation.
                          </p>

                          {lessonsLoading && <p>Loading lessons...</p>}

                          {!lessonsLoading && learningLessons.length === 0 && (
                            <p>
                              No lessons have been proposed for this post yet. Save performance
                              metrics to generate learning suggestions.
                            </p>
                          )}

                          {!lessonsLoading && learningLessons.map((lesson) => (
                            <article className="history-item learning-lesson" key={lesson.id}>
                              <p>{lesson.lesson}</p>
                              <p>
                                Status: <strong>{lesson.status}</strong>
                              </p>

                              {lesson.status === "proposed" && (
                                <div
                                  className="performance-actions"
                                  style={{
                                    display: "flex",
                                    flexWrap: "wrap",
                                    gap: "0.75rem",
                                  }}
                                >
                                  <button
                                    type="button"
                                    className="linkedin-button"
                                    disabled={lessonActionId === lesson.id}
                                    onClick={() => handleLessonDecision(lesson.id, "approve")}
                                  >
                                    {lessonActionId === lesson.id ? "Saving..." : "Approve"}
                                  </button>
                                  <button
                                    type="button"
                                    className="secondary-button"
                                    disabled={lessonActionId === lesson.id}
                                    onClick={() => handleLessonDecision(lesson.id, "reject")}
                                  >
                                    Reject
                                  </button>
                                </div>
                              )}
                            </article>
                          ))}
                        </section>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        </section>


        <footer>CreatorOS · Built for creators who want to grow</footer>
      </main>
    );
  }

  return (
    <main className="login-page">
      <nav className="navbar">
        <div className="brand">
          <span className="brand-icon">C</span>
          <span>CreatorOS</span>
        </div>

        <span className="nav-label">AI Content Studio</span>
      </nav>

      <section className="hero">
        <div className="hero-badge">
          <span className="status-dot" />
          Your personal AI content studio
        </div>

        <h1>
          Create content that
          <br />
          <span>sounds like you.</span>
        </h1>

        <p className="subtitle">
          Learn your unique writing style, create engaging LinkedIn content,
          and improve with every post.
        </p>

        <button className="linkedin-button" onClick={handleLogin}>
          <span className="linkedin-icon">in</span>
          Continue with LinkedIn
          <span className="button-arrow">→</span>
        </button>

        <p className="helper-text">
          Sign in to create your personalized content workspace.
        </p>

        <div className="feature-list">
          <div className="feature">
            <span className="feature-icon">✳</span>
            <div>
              <strong>Your voice</strong>
              <p>Content tailored to your style</p>
            </div>
          </div>

          <div className="feature">
            <span className="feature-icon">↗</span>
            <div>
              <strong>Smarter content</strong>
              <p>Plan, create, and refine</p>
            </div>
          </div>

          <div className="feature">
            <span className="feature-icon">◎</span>
            <div>
              <strong>Continuous learning</strong>
              <p>Improve using performance feedback</p>
            </div>
          </div>
        </div>
      </section>

      {error && <p className="error-message">{error}</p>}

      <footer>CreatorOS · Built for creators who want to grow</footer>
    </main>
  );
}

export default App;
