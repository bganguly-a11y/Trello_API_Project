import { useEffect, useMemo, useState } from "react";
import {
  Clipboard,
  LogOut,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  UserPlus
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function apiRequest(path, { method = "GET", token, body, form } = {}) {
  const headers = {};
  const options = { method, headers };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (form) {
    options.body = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((item) => item.msg).join(", ")
      : data?.detail;
    throw new Error(detail || "Request failed");
  }

  return response.status === 204 ? null : data;
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("trelloToken") || "");
  const [user, setUser] = useState(null);
  const [boards, setBoards] = useState([]);
  const [selectedBoardId, setSelectedBoardId] = useState(null);
  const [boardDetail, setBoardDetail] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isOwner = Boolean(user && boardDetail?.owner_id === user.id);

  const memberOptions = useMemo(() => {
    return boardDetail?.members || [];
  }, [boardDetail]);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setBoards([]);
      setBoardDetail(null);
      return;
    }
    localStorage.setItem("trelloToken", token);
    loadSession(token);
  }, [token]);

  useEffect(() => {
    if (token && selectedBoardId) {
      loadBoard(selectedBoardId);
    }
  }, [selectedBoardId, token]);

  async function run(action, successText) {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const result = await action();
      if (successText) setMessage(successText);
      return result;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function loadSession(activeToken = token) {
    await run(async () => {
      const [profile, boardList] = await Promise.all([
        apiRequest("/auth/me", { token: activeToken }),
        apiRequest("/boards/", { token: activeToken })
      ]);
      setUser(profile);
      setBoards(boardList);
      if (!selectedBoardId && boardList.length > 0) {
        setSelectedBoardId(boardList[0].id);
      }
    });
  }

  async function loadBoard(boardId = selectedBoardId) {
    if (!boardId) return;
    await run(async () => {
      const detail = await apiRequest(`/boards/${boardId}`, { token });
      setBoardDetail(detail);
    });
  }

  async function handleAuth(payload, mode) {
    return await run(async () => {
      if (mode === "reset") {
        await apiRequest("/auth/reset-password", {
          method: "POST",
          body: { email: payload.email, password: payload.password }
        });
        return true;
      }

      if (mode === "register") {
        await apiRequest("/auth/register", { method: "POST", body: payload });
      }
      const login = await apiRequest("/auth/login", {
        method: "POST",
        form: { username: payload.email, password: payload.password }
      });
      setToken(login.access_token);
      return true;
    }, mode === "reset" ? "Password reset. Log in with your new password" : mode === "register" ? "Account created" : "Signed in");
  }

  async function createBoard(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await run(async () => {
      const board = await apiRequest("/boards/", {
        method: "POST",
        token,
        body: {
          name: form.get("name"),
          description: form.get("description") || null
        }
      });
      event.currentTarget.reset();
      await loadSession();
      setSelectedBoardId(board.id);
    }, "Board created");
  }

  async function updateBoard() {
    const name = window.prompt("Board name", boardDetail.name);
    if (!name) return;
    const description = window.prompt("Board description", boardDetail.description || "");
    await run(async () => {
      await apiRequest(`/boards/${boardDetail.id}`, {
        method: "PATCH",
        token,
        body: { name, description }
      });
      await loadSession();
      await loadBoard(boardDetail.id);
    }, "Board updated");
  }

  async function deleteBoard() {
    if (!window.confirm(`Delete ${boardDetail.name}?`)) return;
    await run(async () => {
      await apiRequest(`/boards/${boardDetail.id}`, { method: "DELETE", token });
      setBoardDetail(null);
      setSelectedBoardId(null);
      await loadSession();
    }, "Board deleted");
  }

  async function createInvitation() {
    await run(async () => {
      const invitation = await apiRequest(`/boards/${boardDetail.id}/invitations`, {
        method: "POST",
        token
      });
      await navigator.clipboard?.writeText(invitation.token);
      await loadBoard(boardDetail.id);
      setMessage(`Invitation token: ${invitation.token}`);
    });
  }

  async function acceptInvitation(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await run(async () => {
      const board = await apiRequest("/invitations/accept", {
        method: "POST",
        token,
        body: { token: form.get("token") }
      });
      event.currentTarget.reset();
      await loadSession();
      setSelectedBoardId(board.id);
    }, "Invitation accepted");
  }

  async function createSection(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await run(async () => {
      await apiRequest(`/boards/${boardDetail.id}/sections`, {
        method: "POST",
        token,
        body: {
          name: form.get("name"),
          description: form.get("description") || null
        }
      });
      event.currentTarget.reset();
      await loadBoard(boardDetail.id);
    }, "Section created");
  }

  async function updateSection(section) {
    const name = window.prompt("Section name", section.name);
    if (!name) return;
    const description = window.prompt("Section description", section.description || "");
    await run(async () => {
      await apiRequest(`/sections/${section.id}`, {
        method: "PATCH",
        token,
        body: { name, description }
      });
      await loadBoard(boardDetail.id);
    }, "Section updated");
  }

  async function deleteSection(section) {
    if (!window.confirm(`Delete ${section.name}?`)) return;
    await run(async () => {
      await apiRequest(`/sections/${section.id}`, { method: "DELETE", token });
      await loadBoard(boardDetail.id);
    }, "Section deleted");
  }

  async function createTicket(event, sectionId) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const assigneeId = form.get("assignee_id");
    await run(async () => {
      await apiRequest(`/sections/${sectionId}/tickets`, {
        method: "POST",
        token,
        body: {
          name: form.get("name"),
          description: form.get("description") || null,
          assignee_id: assigneeId ? Number(assigneeId) : null
        }
      });
      event.currentTarget.reset();
      await loadBoard(boardDetail.id);
    }, "Ticket created");
  }

  async function updateTicket(ticket, patch, successText = "Ticket updated") {
    await run(async () => {
      await apiRequest(`/tickets/${ticket.id}`, {
        method: "PATCH",
        token,
        body: patch
      });
      await loadBoard(boardDetail.id);
    }, successText);
  }

  async function editTicket(ticket) {
    const name = window.prompt("Ticket name", ticket.name);
    if (!name) return;
    const description = window.prompt("Ticket description", ticket.description || "");
    await updateTicket(ticket, { name, description });
  }

  async function deleteTicket(ticket) {
    if (!window.confirm(`Delete ${ticket.name}?`)) return;
    await run(async () => {
      await apiRequest(`/tickets/${ticket.id}`, { method: "DELETE", token });
      await loadBoard(boardDetail.id);
    }, "Ticket deleted");
  }

  function logout() {
    localStorage.removeItem("trelloToken");
    setToken("");
    setSelectedBoardId(null);
  }

  if (!token) {
    return <AuthScreen onSubmit={handleAuth} loading={loading} error={error} message={message} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <div>
            <p className="eyebrow">Trello API</p>
            <h1>{user?.name || "Workspace"}</h1>
          </div>
          <button className="icon-button" onClick={logout} title="Log out">
            <LogOut size={18} />
          </button>
        </div>

        <form className="stacked-form" onSubmit={acceptInvitation}>
          <label htmlFor="invite-token">Invitation token</label>
          <div className="inline-row">
            <input id="invite-token" name="token" placeholder="Paste token" required />
            <button className="icon-button" type="submit" title="Accept invitation">
              <UserPlus size={18} />
            </button>
          </div>
        </form>

        <form className="stacked-form" onSubmit={createBoard}>
          <label htmlFor="board-name">New board</label>
          <input id="board-name" name="name" placeholder="Board name" required />
          <textarea name="description" placeholder="Description" rows="3" />
          <button type="submit">
            <Plus size={16} />
            Create board
          </button>
        </form>

        <nav className="board-list" aria-label="Boards">
          {boards.map((board) => (
            <button
              key={board.id}
              className={board.id === selectedBoardId ? "active" : ""}
              onClick={() => setSelectedBoardId(board.id)}
            >
              <span>{board.name}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="workspace">
        <StatusBar loading={loading} message={message} error={error} />

        {!boardDetail ? (
          <section className="empty-state">
            <h2>Create or select a board</h2>
          </section>
        ) : (
          <>
            <section className="board-header">
              <div>
                <p className="eyebrow">{isOwner ? "Owner" : "Member"}</p>
                <h2>{boardDetail.name}</h2>
                {boardDetail.description && <p>{boardDetail.description}</p>}
              </div>
              <div className="header-actions">
                <button className="icon-button" onClick={() => loadBoard(boardDetail.id)} title="Refresh">
                  <RefreshCw size={18} />
                </button>
                {isOwner && (
                  <>
                    <button onClick={createInvitation}>
                      <Clipboard size={16} />
                      Invite
                    </button>
                    <button onClick={updateBoard}>
                      <Save size={16} />
                      Save
                    </button>
                    <button className="danger" onClick={deleteBoard}>
                      <Trash2 size={16} />
                      Delete
                    </button>
                  </>
                )}
              </div>
            </section>

            <section className="members-strip" aria-label="Board members">
              {memberOptions.map((member) => (
                <span key={member.user_id}>
                  {member.name}
                  {member.is_owner ? " owner" : ""}
                </span>
              ))}
            </section>

            {isOwner && (
              <form className="section-form" onSubmit={createSection}>
                <input name="name" placeholder="Section name" required />
                <input name="description" placeholder="Description" />
                <button type="submit">
                  <Plus size={16} />
                  Section
                </button>
              </form>
            )}

            <section className="kanban-board" aria-label="Sections">
              {boardDetail.sections.map((section) => (
                <SectionColumn
                  key={section.id}
                  section={section}
                  sections={boardDetail.sections}
                  members={memberOptions}
                  user={user}
                  isOwner={isOwner}
                  onCreateTicket={createTicket}
                  onUpdateSection={updateSection}
                  onDeleteSection={deleteSection}
                  onEditTicket={editTicket}
                  onDeleteTicket={deleteTicket}
                  onUpdateTicket={updateTicket}
                />
              ))}
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function AuthScreen({ onSubmit, loading, error, message }) {
  const [mode, setMode] = useState("login");
  const [lastSubmittedMode, setLastSubmittedMode] = useState(null);

  async function submit(event) {
    event.preventDefault();
    setLastSubmittedMode(mode);
    const form = new FormData(event.currentTarget);
    if (mode === "reset" && form.get("password") !== form.get("confirm_password")) {
      window.alert("Passwords do not match");
      return;
    }

    const success = await onSubmit(
      {
        name: form.get("name"),
        email: form.get("email"),
        password: form.get("password")
      },
      mode
    );

    if (success && mode === "reset") {
      event.currentTarget.reset();
      setMode("login");
    }
  }

  const title = mode === "reset" ? "Reset password" : mode === "login" ? "Sign in" : "Create account";

  return (
    <main className="auth-layout">
      <section className="auth-panel">
        <div>
          <p className="eyebrow">Trello API</p>
          <h1>{title}</h1>
        </div>
        {mode !== "reset" && (
          <div className="segmented">
            <button
              className={mode === "login" ? "active" : ""}
              onClick={() => setMode("login")}
              type="button"
            >
              Login
            </button>
            <button
              className={mode === "register" ? "active" : ""}
              onClick={() => setMode("register")}
              type="button"
            >
              Register
            </button>
          </div>
        )}
        <form className="stacked-form" onSubmit={submit}>
          {mode === "register" && (
            <>
              <label htmlFor="name">Name</label>
              <input id="name" name="name" placeholder="Your name" required />
            </>
          )}
          <label htmlFor="email">Email</label>
          <input id="email" name="email" placeholder="you@example.com" type="email" required />
          <label htmlFor="password">{mode === "reset" ? "New password" : "Password"}</label>
          <input id="password" name="password" placeholder="secret123" type="password" minLength="6" required />
          {mode === "reset" && (
            <>
              <label htmlFor="confirm-password">Confirm password</label>
              <input id="confirm-password" name="confirm_password" placeholder="secret123" type="password" minLength="6" required />
            </>
          )}
          <button type="submit" disabled={loading}>
            {mode === "reset" ? "Reset password" : mode === "login" ? "Login" : "Register"}
          </button>
          {mode === "login" && (
            <button className="link-button" type="button" onClick={() => setMode("reset")}>
              Forgot password?
            </button>
          )}
          {mode === "reset" && (
            <button className="link-button" type="button" onClick={() => setMode("login")}>
              Back to login
            </button>
          )}
          {message && <p className="success-text">{message}</p>}
          {error && lastSubmittedMode === mode && <p className="error-text">{error}</p>}
        </form>
      </section>
    </main>
  );
}

function StatusBar({ loading, message, error }) {
  if (!loading && !message && !error) return null;
  return (
    <div className={`status-bar ${error ? "error" : ""}`}>
      {loading ? "Working..." : error || message}
    </div>
  );
}

function SectionColumn({
  section,
  sections,
  members,
  user,
  isOwner,
  onCreateTicket,
  onUpdateSection,
  onDeleteSection,
  onEditTicket,
  onDeleteTicket,
  onUpdateTicket
}) {
  return (
    <article className="section-column">
      <header>
        <div>
          <h3>{section.name}</h3>
          {section.description && <p>{section.description}</p>}
        </div>
        {isOwner && (
          <div className="small-actions">
            <button className="icon-button" onClick={() => onUpdateSection(section)} title="Edit section">
              <Save size={16} />
            </button>
            <button className="icon-button danger" onClick={() => onDeleteSection(section)} title="Delete section">
              <Trash2 size={16} />
            </button>
          </div>
        )}
      </header>

      <div className="ticket-list">
        {section.tickets.map((ticket) => {
          const canEdit = isOwner || ticket.creator_id === user?.id;
          return (
            <article className="ticket-card" key={ticket.id}>
              <div>
                <h4>{ticket.name}</h4>
                {ticket.description && <p>{ticket.description}</p>}
              </div>
              <TicketMeta ticket={ticket} members={members} />
              {canEdit && (
                <div className="ticket-controls">
                  <select
                    value={ticket.section_id}
                    onChange={(event) =>
                      onUpdateTicket(ticket, { section_id: Number(event.target.value) }, "Ticket moved")
                    }
                  >
                    {sections.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                  <select
                    value={ticket.assignee_id || ""}
                    onChange={(event) =>
                      onUpdateTicket(ticket, {
                        assignee_id: event.target.value ? Number(event.target.value) : null
                      })
                    }
                  >
                    <option value="">Unassigned</option>
                    {members.map((member) => (
                      <option key={member.user_id} value={member.user_id}>
                        {member.name}
                      </option>
                    ))}
                  </select>
                  <button onClick={() => onEditTicket(ticket)}>
                    <Save size={16} />
                    Edit
                  </button>
                  <button className="danger" onClick={() => onDeleteTicket(ticket)}>
                    <Trash2 size={16} />
                    Delete
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>

      <form className="ticket-form" onSubmit={(event) => onCreateTicket(event, section.id)}>
        <input name="name" placeholder="Ticket name" required />
        <textarea name="description" placeholder="Description" rows="2" />
        <select name="assignee_id" defaultValue="">
          <option value="">Unassigned</option>
          {members.map((member) => (
            <option key={member.user_id} value={member.user_id}>
              {member.name}
            </option>
          ))}
        </select>
        <button type="submit">
          <Plus size={16} />
          Ticket
        </button>
      </form>
    </article>
  );
}

function TicketMeta({ ticket, members }) {
  const creator = members.find((member) => member.user_id === ticket.creator_id);
  const assignee = members.find((member) => member.user_id === ticket.assignee_id);

  return (
    <div className="ticket-meta">
      <span>By {creator?.name || "member"}</span>
      <span>{assignee ? `To ${assignee.name}` : "Unassigned"}</span>
    </div>
  );
}

export default App;
