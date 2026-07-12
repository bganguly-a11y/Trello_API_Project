import { useEffect, useMemo, useState, useRef } from "react";
import {
  Clipboard,
  LogOut,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  UserPlus,
  Search,
  Star,
  Bell,
  HelpCircle,
  Check,
  X,
  Edit2,
  ChevronDown,
  AlignLeft,
  Paperclip,
  CheckSquare,
  Eye,
  Settings,
  Menu,
  Shield,
  Calendar,
  Users,
  Info,
  ArrowRight,
  Filter,
  Layers,
  Inbox,
  LayoutDashboard
} from "lucide-react";

// In dev, use the Vite proxy (same-origin). In production, default to same-origin
// when served from FastAPI; override with VITE_API_URL when deployed separately.
const API_BASE = import.meta.env.VITE_API_URL ?? "";

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

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new Error(
      "Cannot reach the API server. Start the backend with: uvicorn app.main:app --reload"
    );
  }

  // 204/205 responses have no body — skip JSON parsing entirely
  if (response.status === 204 || response.status === 205) {
    return null;
  }

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

  return data;
}

// Helper for member avatar colors
function getAvatarColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const h = Math.abs(hash % 360);
  return `hsl(${h}, 60%, 45%)`;
}

function getInitials(name) {
  if (!name) return "?";
  const parts = name.split(" ");
  if (parts.length > 1) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return parts[0].substring(0, 2).toUpperCase();
}

function App() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState(null);
  const [boards, setBoards] = useState([]);
  const [selectedBoardId, setSelectedBoardId] = useState(null);
  const [boardDetail, setBoardDetail] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Custom UI UX states
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [starredBoards, setStarredBoards] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("starredBoards")) || [];
    } catch {
      return [];
    }
  });
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [createBoardModalOpen, setCreateBoardModalOpen] = useState(false);
  const [confirmModal, setConfirmModal] = useState(null); // { message, onConfirm }
  const [boardSettingsOpen, setBoardSettingsOpen] = useState(false);

  // Board settings inline edit states
  const [editingBoardDesc, setEditingBoardDesc] = useState("");
  const [editingDescInPanel, setEditingDescInPanel] = useState(false);
  const [editingNameInPanel, setEditingNameInPanel] = useState(false);
  const [editingBoardNamePanel, setEditingBoardNamePanel] = useState("");

  // Refs for click-outside behavior
  const navbarRef = useRef(null);
  const boardSettingsPanelRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("starredBoards", JSON.stringify(starredBoards));
  }, [starredBoards]);

  const isStarred = useMemo(() => {
    return boardDetail && starredBoards.includes(boardDetail.id);
  }, [boardDetail, starredBoards]);

  const toggleStarBoard = (boardId) => {
    setStarredBoards(prev =>
      prev.includes(boardId) ? prev.filter(id => id !== boardId) : [...prev, boardId]
    );
  };

  const toggleDropdown = (name) => {
    setActiveDropdown(prev => prev === name ? null : name);
  };

  // Click-outside handler for nav dropdowns
  useEffect(() => {
    if (!activeDropdown) return;
    function handleClickOutside(e) {
      if (navbarRef.current && !navbarRef.current.contains(e.target)) {
        setActiveDropdown(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [activeDropdown]);

  // Click-outside handler for board settings panel
  useEffect(() => {
    if (!boardSettingsOpen) return;
    function handleClickOutside(e) {
      if (boardSettingsPanelRef.current && !boardSettingsPanelRef.current.contains(e.target)) {
        setBoardSettingsOpen(false);
        setEditingDescInPanel(false);
        setEditingNameInPanel(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [boardSettingsOpen]);

  // Inline section additions & edits
  const [addingSection, setAddingSection] = useState(false);
  const [newSectionName, setNewSectionName] = useState("");
  const [editingSectionId, setEditingSectionId] = useState(null);
  const [editingSectionName, setEditingSectionName] = useState("");

  // Inline ticket additions
  const [addingTicketSectionId, setAddingTicketSectionId] = useState(null);
  const [newTicketName, setNewTicketName] = useState("");

  // Inline Board rename
  const [editingBoardTitle, setEditingBoardTitle] = useState(false);
  const [editingBoardName, setEditingBoardName] = useState("");

  const isOwner = Boolean(user && boardDetail?.owner_id === user.id);

  const memberOptions = useMemo(() => {
    return boardDetail?.members || [];
  }, [boardDetail]);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setBoards([]);
      setBoardDetail(null);
      localStorage.removeItem("trelloToken");
      return;
    }
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
      if (successText) {
        setMessage(successText);
        setTimeout(() => setMessage(""), 4000);
      }
      return result;
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(""), 5000);
      if (err.message.includes("validate credentials") || err.message.includes("Not authenticated")) {
        setToken("");
        localStorage.removeItem("trelloToken");
      }
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

  async function createBoard(name, description) {
    if (!name) return;
    await run(async () => {
      const board = await apiRequest("/boards/", {
        method: "POST",
        token,
        body: { name, description: description || null }
      });

      // Auto-create the three default lists for every new board
      const defaultLists = ["To Do", "In Progress", "Completed"];
      for (const listName of defaultLists) {
        await apiRequest(`/boards/${board.id}/sections`, {
          method: "POST",
          token,
          body: { name: listName, description: null }
        });
      }

      setCreateBoardModalOpen(false);
      await loadSession();
      setSelectedBoardId(board.id);

      // Load the full board detail so the columns appear immediately
      const detail = await apiRequest(`/boards/${board.id}`, { token });
      setBoardDetail(detail);
    }, "Board created");
  }

  async function createBoardFromTemplate(templateName, sectionsList) {
    await run(async () => {
      const board = await apiRequest("/boards/", {
        method: "POST",
        token,
        body: { name: templateName, description: `Created from ${templateName} template.` }
      });
      await loadSession(token);
      setSelectedBoardId(board.id);
      setActiveDropdown(null);
      for (const sectionName of sectionsList) {
        await apiRequest(`/boards/${board.id}/sections`, {
          method: "POST",
          token,
          body: { name: sectionName, description: null }
        });
      }
      const detail = await apiRequest(`/boards/${board.id}`, { token });
      setBoardDetail(detail);
    }, `Board "${templateName}" created from template`);
  }

  async function updateBoard(name, description) {
    if (!name) return;
    await run(async () => {
      await apiRequest(`/boards/${boardDetail.id}`, {
        method: "PATCH",
        token,
        body: { name, description: description || null }
      });
      await loadSession();
      await loadBoard(boardDetail.id);
    }, "Board updated");
  }

  async function deleteBoard() {
    setConfirmModal({
      message: `Are you sure you want to delete board "${boardDetail.name}"? This action cannot be undone.`,
      onConfirm: async () => {
        await run(async () => {
          await apiRequest(`/boards/${boardDetail.id}`, { method: "DELETE", token });
          setBoardDetail(null);
          setSelectedBoardId(null);
          setConfirmModal(null);
          setBoardSettingsOpen(false);
          await loadSession();
        }, "Board deleted");
      }
    });
  }

  async function createInvitation() {
    await run(async () => {
      const invitation = await apiRequest(`/boards/${boardDetail.id}/invitations`, {
        method: "POST",
        token
      });
      await navigator.clipboard?.writeText(invitation.token);
      await loadBoard(boardDetail.id);
      setMessage(`Invitation token copied to clipboard! Token: ${invitation.token}`);
      setTimeout(() => setMessage(""), 5000);
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
    if (!newSectionName.trim()) return;
    await run(async () => {
      await apiRequest(`/boards/${boardDetail.id}/sections`, {
        method: "POST",
        token,
        body: {
          name: newSectionName,
          description: null
        }
      });
      setNewSectionName("");
      setAddingSection(false);
      await loadBoard(boardDetail.id);
    }, "List created");
  }

  async function updateSection(section, name, description) {
    if (!name) return;
    await run(async () => {
      await apiRequest(`/sections/${section.id}`, {
        method: "PATCH",
        token,
        body: { name, description: description || null }
      });
      await loadBoard(boardDetail.id);
    }, "Section updated");
  }

  async function deleteSection(section) {
    setConfirmModal({
      message: `Delete list "${section.name}" and all of its cards?`,
      onConfirm: async () => {
        await run(async () => {
          await apiRequest(`/sections/${section.id}`, { method: "DELETE", token });
          setConfirmModal(null);
          await loadBoard(boardDetail.id);
        }, "Section deleted");
      }
    });
  }

  async function createTicket(sectionId) {
    if (!newTicketName.trim()) return;
    await run(async () => {
      await apiRequest(`/sections/${sectionId}/tickets`, {
        method: "POST",
        token,
        body: {
          name: newTicketName,
          description: null,
          assignee_id: null
        }
      });
      setNewTicketName("");
      setAddingTicketSectionId(null);
      await loadBoard(boardDetail.id);
    }, "Card created");
  }

  async function updateTicket(ticket, patch, successText = "Ticket updated") {
    await run(async () => {
      const updated = await apiRequest(`/tickets/${ticket.id}`, {
        method: "PATCH",
        token,
        body: patch
      });
      await loadBoard(boardDetail.id);
      // Update selected ticket in modal if open
      if (selectedTicket && selectedTicket.id === ticket.id) {
        setSelectedTicket(prev => ({ ...prev, ...patch }));
      }
    }, successText);
  }

  async function deleteTicket(ticket) {
    setConfirmModal({
      message: `Are you sure you want to delete card "${ticket.name}"?`,
      onConfirm: async () => {
        await run(async () => {
          await apiRequest(`/tickets/${ticket.id}`, { method: "DELETE", token });
          setConfirmModal(null);
          setSelectedTicket(null);
          await loadBoard(boardDetail.id);
        }, "Card deleted");
      }
    });
  }

  function logout() {
    localStorage.removeItem("trelloToken");
    setToken("");
    setSelectedBoardId(null);
  }

  // Board rename handler
  function saveBoardRename() {
    if (editingBoardName.trim() && editingBoardName !== boardDetail.name) {
      updateBoard(editingBoardName, boardDetail.description);
    }
    setEditingBoardTitle(false);
  }

  // Section rename handler
  function saveSectionRename(section) {
    if (editingSectionName.trim() && editingSectionName !== section.name) {
      updateSection(section, editingSectionName, section.description);
    }
    setEditingSectionId(null);
  }

  if (!token) {
    return <AuthScreen onSubmit={handleAuth} loading={loading} error={error} message={message} />;
  }

  return (
    <div className="app-shell">
      {/* Top Header Navigation */}
      <header className="trello-navbar" ref={navbarRef}>
        <div className="navbar-left">
          <button className="nav-icon-btn sidebar-trigger" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Toggle sidebar">
            <Menu size={20} />
          </button>

          <div className="trello-logo">
            <LayoutDashboard size={18} className="logo-icon" />
            <span className="logo-text">Trello</span>
          </div>

          <nav className="navbar-links" aria-label="Main menu">
            {/* Workspaces Dropdown */}
            <div className="nav-dropdown-container">
              <button className={`nav-btn ${activeDropdown === 'workspaces' ? 'active' : ''}`} onClick={() => toggleDropdown('workspaces')}>
                Workspaces <ChevronDown size={14} />
              </button>
              {activeDropdown === 'workspaces' && (
                <div className="nav-dropdown-menu">
                  <div className="dropdown-section-header">Current Workspace</div>
                  <div className="workspace-dropdown-item">
                    <div className="workspace-dropdown-icon">
                      {getInitials(user?.name || "Workspace")}
                    </div>
                    <div>
                      <div className="workspace-item-title">{user?.name || "My Workspace"}</div>
                      <div className="workspace-item-desc">Free Workspace</div>
                    </div>
                  </div>
                  <div className="dropdown-divider"></div>
                  <div className="dropdown-section-header">Your Boards</div>
                  <div className="dropdown-scroll-container">
                    {boards.map(b => (
                      <button
                        key={b.id}
                        className={`dropdown-menu-item ${b.id === selectedBoardId ? 'active' : ''}`}
                        onClick={() => { setSelectedBoardId(b.id); setActiveDropdown(null); }}
                      >
                        <span className="board-color-indicator"></span>
                        <span className="board-title-text">{b.name}</span>
                      </button>
                    ))}
                  </div>
                  <div className="dropdown-divider"></div>
                  <button className="dropdown-action-btn-menu" onClick={() => { setCreateBoardModalOpen(true); setActiveDropdown(null); }}>
                    <Plus size={14} /> Create Board
                  </button>
                </div>
              )}
            </div>

            {/* Recent Dropdown */}
            <div className="nav-dropdown-container">
              <button className={`nav-btn ${activeDropdown === 'recent' ? 'active' : ''}`} onClick={() => toggleDropdown('recent')}>
                Recent <ChevronDown size={14} />
              </button>
              {activeDropdown === 'recent' && (
                <div className="nav-dropdown-menu">
                  <div className="dropdown-section-header">Recent Boards</div>
                  <div className="dropdown-scroll-container">
                    {boards.length === 0 ? (
                      <div className="dropdown-empty-text">No recent boards</div>
                    ) : (
                      boards.slice(0, 5).map(b => (
                        <button
                          key={b.id}
                          className={`dropdown-menu-item ${b.id === selectedBoardId ? 'active' : ''}`}
                          onClick={() => { setSelectedBoardId(b.id); setActiveDropdown(null); }}
                        >
                          <span className="board-color-indicator"></span>
                          <span className="board-title-text">{b.name}</span>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Starred Dropdown */}
            <div className="nav-dropdown-container">
              <button className={`nav-btn ${activeDropdown === 'starred' ? 'active' : ''}`} onClick={() => toggleDropdown('starred')}>
                Starred <ChevronDown size={14} />
              </button>
              {activeDropdown === 'starred' && (
                <div className="nav-dropdown-menu">
                  <div className="dropdown-section-header">Starred Boards</div>
                  <div className="dropdown-scroll-container">
                    {boards.filter(b => starredBoards.includes(b.id)).length === 0 ? (
                      <div className="dropdown-empty-text">
                        No starred boards. Click the star icon next to a board title to star it.
                      </div>
                    ) : (
                      boards.filter(b => starredBoards.includes(b.id)).map(b => (
                        <button
                          key={b.id}
                          className={`dropdown-menu-item ${b.id === selectedBoardId ? 'active' : ''}`}
                          onClick={() => { setSelectedBoardId(b.id); setActiveDropdown(null); }}
                        >
                          <span className="board-color-indicator"></span>
                          <span className="board-title-text">{b.name}</span>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Templates Dropdown */}
            <div className="nav-dropdown-container">
              <button className={`nav-btn ${activeDropdown === 'templates' ? 'active' : ''}`} onClick={() => toggleDropdown('templates')}>
                Templates <ChevronDown size={14} />
              </button>
              {activeDropdown === 'templates' && (
                <div className="nav-dropdown-menu">
                  <div className="dropdown-section-header">Create from Template</div>
                  <button 
                    className="dropdown-menu-item-template"
                    onClick={() => createBoardFromTemplate("Project Management", ["Backlog", "In Progress", "Review", "Done"])}
                  >
                    <div className="template-item-title">Project Management</div>
                    <div className="template-item-desc">Lists: Backlog, In Progress, Review, Done</div>
                  </button>
                  <button 
                    className="dropdown-menu-item-template"
                    onClick={() => createBoardFromTemplate("Weekly Planner", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])}
                  >
                    <div className="template-item-title">Weekly Planner</div>
                    <div className="template-item-desc">Lists: Monday, Tuesday, Wednesday, Thursday, Friday</div>
                  </button>
                  <button 
                    className="dropdown-menu-item-template"
                    onClick={() => createBoardFromTemplate("Sales Pipeline", ["Leads", "Contacted", "Proposal", "Won"])}
                  >
                    <div className="template-item-title">Sales Pipeline</div>
                    <div className="template-item-desc">Lists: Leads, Contacted, Proposal, Won</div>
                  </button>
                </div>
              )}
            </div>

            <button className="nav-create-btn" onClick={() => setCreateBoardModalOpen(true)}>
              <Plus size={16} /> Create
            </button>
          </nav>
        </div>

        <div className="navbar-right">
          <div className="user-profile-menu">
            <div
              className="user-avatar"
              style={{ backgroundColor: getAvatarColor(user?.name || "User") }}
              title={`${user?.name} (${user?.email})`}
            >
              {getInitials(user?.name)}
            </div>
            <button className="logout-btn-header" onClick={logout} title="Sign Out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Wrapper */}
      <div className={`workspace-wrapper ${sidebarOpen ? "sidebar-open" : "sidebar-collapsed"}`}>

        {/* Left Collapsible Sidebar */}
        <aside className="trello-sidebar" aria-label="Boards navigation">
          <div className="sidebar-header">
            <div className="workspace-branding">
              <div className="workspace-icon">
                {getInitials(user?.name || "Workspace")}
              </div>
              <div className="workspace-info">
                <h3>{user?.name || "My Workspace"}</h3>
                <span className="badge-premium">Free Workspace</span>
              </div>
            </div>
          </div>

          <div className="sidebar-divider"></div>

          <div className="sidebar-section">
            <div className="section-title-row">
              <h4>Your Boards</h4>
              <button className="sidebar-action-btn" onClick={() => setCreateBoardModalOpen(true)} title="Create Board">
                <Plus size={16} />
              </button>
            </div>
            <nav className="sidebar-boards-list" aria-label="Boards">
              {boards.map((board) => (
                <button
                  key={board.id}
                  className={`sidebar-board-item ${board.id === selectedBoardId ? "active" : ""}`}
                  onClick={() => setSelectedBoardId(board.id)}
                >
                  <span className="board-color-indicator"></span>
                  <span className="board-title-text">{board.name}</span>
                  {board.id === selectedBoardId && <span className="active-dot"></span>}
                </button>
              ))}
            </nav>
          </div>

          <div className="sidebar-divider"></div>

          <div className="sidebar-section">
            <h4>Join a Board</h4>
            <form className="join-board-form" onSubmit={acceptInvitation}>
              <input name="token" placeholder="Paste invitation token" required className="sidebar-input" />
              <button type="submit" className="sidebar-submit-btn">
                <UserPlus size={16} /> Join Board
              </button>
            </form>
          </div>
        </aside>

        {/* Board Canvas Area */}
        <main className="trello-canvas">

          <StatusBar error={error} message={message} loading={loading} />

          {!boardDetail ? (
            <div className="empty-state-canvas">
              <div className="empty-state-content">
                <Layers size={64} className="empty-icon" />
                <h2>Welcome to Trello clone!</h2>
                <p>Create a new board in the sidebar, or join an existing board with an invitation token.</p>
                <button className="primary-btn" onClick={() => setCreateBoardModalOpen(true)}>
                  <Plus size={16} /> Create Your First Board
                </button>
              </div>
            </div>
          ) : (
            <div className="board-main-container">
              {/* Board Subheader */}
              <div className="board-subheader">
                <div className="subheader-left">
                  {editingBoardTitle && isOwner ? (
                    <input
                      type="text"
                      value={editingBoardName}
                      onChange={(e) => setEditingBoardName(e.target.value)}
                      onBlur={saveBoardRename}
                      onKeyDown={(e) => e.key === "Enter" && saveBoardRename()}
                      autoFocus
                      className="board-title-input"
                    />
                  ) : (
                    <h1 className="board-title" onClick={() => { if (isOwner) { setEditingBoardName(boardDetail.name); setEditingBoardTitle(true); } }}>
                      {boardDetail.name}
                    </h1>
                  )}

                  <button 
                    className={`board-header-btn star-btn ${isStarred ? "starred" : ""}`} 
                    onClick={() => toggleStarBoard(boardDetail.id)}
                    title={isStarred ? "Unstar board" : "Star board"}
                  >
                    <Star size={16} />
                  </button>

                  <span className="subheader-divider"></span>

                  <button className="board-header-btn" onClick={() => setBoardSettingsOpen(!boardSettingsOpen)}>
                    <Users size={16} /> <span className="btn-label">Workspace Visible</span> <ChevronDown size={12} />
                  </button>

                  {/* Board Settings Dropdown */}
                  {boardSettingsOpen && (
                    <div className="board-settings-dropdown" ref={boardSettingsPanelRef}>
                      <div className="dropdown-header">
                        <h3>Board Administration</h3>
                        <button className="close-btn" onClick={() => { setBoardSettingsOpen(false); setEditingDescInPanel(false); setEditingNameInPanel(false); }}><X size={16} /></button>
                      </div>
                      <div className="dropdown-content">
                        <p className="dropdown-role">
                          You are: <strong>{isOwner ? "Owner" : "Member"}</strong>
                        </p>

                        {/* Description Section */}
                        <div className="panel-field-group">
                          <label className="panel-field-label">Description</label>
                          {editingDescInPanel ? (
                            <div className="panel-edit-row">
                              <textarea
                                className="panel-edit-textarea"
                                value={editingBoardDesc}
                                onChange={(e) => setEditingBoardDesc(e.target.value)}
                                rows={3}
                                autoFocus
                                placeholder="Add a board description..."
                              />
                              <div className="panel-edit-actions">
                                <button className="primary-btn-sm" onClick={() => {
                                  updateBoard(boardDetail.name, editingBoardDesc);
                                  setEditingDescInPanel(false);
                                }}>Save</button>
                                <button className="close-btn-sm" onClick={() => setEditingDescInPanel(false)}><X size={14} /></button>
                              </div>
                            </div>
                          ) : (
                            <div
                              className={`panel-field-value ${isOwner ? "editable" : ""}`}
                              onClick={() => {
                                if (isOwner) {
                                  setEditingBoardDesc(boardDetail.description || "");
                                  setEditingDescInPanel(true);
                                }
                              }}
                            >
                              {boardDetail.description || <span className="placeholder-text">No description. {isOwner ? "Click to add one." : ""}</span>}
                            </div>
                          )}
                        </div>

                        {isOwner && (
                          <>
                            {/* Rename Board */}
                            <div className="panel-field-group">
                              <label className="panel-field-label">Rename Board</label>
                              {editingNameInPanel ? (
                                <div className="panel-edit-row">
                                  <input
                                    className="panel-edit-input"
                                    value={editingBoardNamePanel}
                                    onChange={(e) => setEditingBoardNamePanel(e.target.value)}
                                    autoFocus
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter" && editingBoardNamePanel.trim()) {
                                        updateBoard(editingBoardNamePanel, boardDetail.description);
                                        setEditingNameInPanel(false);
                                        setBoardSettingsOpen(false);
                                      }
                                      if (e.key === "Escape") setEditingNameInPanel(false);
                                    }}
                                  />
                                  <div className="panel-edit-actions">
                                    <button className="primary-btn-sm" onClick={() => {
                                      if (editingBoardNamePanel.trim()) {
                                        updateBoard(editingBoardNamePanel, boardDetail.description);
                                        setEditingNameInPanel(false);
                                        setBoardSettingsOpen(false);
                                      }
                                    }}>Rename</button>
                                    <button className="close-btn-sm" onClick={() => setEditingNameInPanel(false)}><X size={14} /></button>
                                  </div>
                                </div>
                              ) : (
                                <button className="dropdown-action-btn secondary" onClick={() => {
                                  setEditingBoardNamePanel(boardDetail.name);
                                  setEditingNameInPanel(true);
                                }}>
                                  <Edit2 size={13} /> Rename Board
                                </button>
                              )}
                            </div>

                            {/* Delete Board */}
                            <div className="panel-field-group">
                              <button className="dropdown-action-btn danger" onClick={() => {
                                setBoardSettingsOpen(false);
                                deleteBoard();
                              }}>
                                <Trash2 size={13} /> Delete Board
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  )}


                  <span className="subheader-divider"></span>

                  {/* Member Avatars list */}
                  <div className="board-members-stack" aria-label="Board members">
                    {memberOptions.slice(0, 5).map((member) => (
                      <div
                        key={member.user_id}
                        className="member-avatar-circle"
                        style={{ backgroundColor: getAvatarColor(member.name) }}
                        title={`${member.name} ${member.is_owner ? "(Owner)" : ""}`}
                      >
                        {getInitials(member.name)}
                      </div>
                    ))}
                    {memberOptions.length > 5 && (
                      <div className="member-avatar-circle remaining" title={`${memberOptions.length - 5} more members`}>
                        +{memberOptions.length - 5}
                      </div>
                    )}
                  </div>

                  {isOwner && (
                    <button className="board-header-share-btn" onClick={createInvitation}>
                      <UserPlus size={16} /> Invite
                    </button>
                  )}
                </div>
              </div>

              {/* Kanban Columns (Scrollable Area) */}
              <div className="kanban-columns-scroller">
                <div className="kanban-columns-container">
                  {boardDetail.sections.map((section) => (
                    <div key={section.id} className="kanban-list">
                      {/* List Header */}
                      <div className="list-header">
                        {editingSectionId === section.id && isOwner ? (
                          <input
                            type="text"
                            value={editingSectionName}
                            onChange={(e) => setEditingSectionName(e.target.value)}
                            onBlur={() => saveSectionRename(section)}
                            onKeyDown={(e) => e.key === "Enter" && saveSectionRename(section)}
                            autoFocus
                            className="list-title-input"
                          />
                        ) : (
                          <h3 
                            className="list-title" 
                            onClick={() => { if (isOwner) { setEditingSectionId(section.id); setEditingSectionName(section.name); } }}
                          >
                            {section.name}
                          </h3>
                        )}
                        
                        <div className="list-header-actions">
                          <span className="card-count-badge">
                            {section.tickets?.length || 0}
                          </span>
                          {isOwner && (
                            <button className="list-menu-btn" onClick={() => deleteSection(section)} title="Delete list">
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* List Cards list */}
                      <div className="list-cards" aria-label="Cards list">
                        {section.tickets?.map((ticket, index) => {
                          const showCover = index % 3 === 0;
                          const coverColor = showCover ? `hsl(${(index * 75) % 360}, 65%, 45%)` : null;

                          return (
                            <div 
                              key={ticket.id} 
                              className="card-item"
                              onClick={() => setSelectedTicket({ ...ticket, section_name: section.name })}
                            >
                              {showCover && (
                                <div className="card-cover-color" style={{ backgroundColor: coverColor }} />
                              )}
                              <div className="card-content-body">
                                <h4 className="card-title-text">{ticket.name}</h4>
                                
                                <div className="card-footer-badges">
                                  <div className="badges-left">
                                    {ticket.description && (
                                      <div className="badge-item" title="This card has a description.">
                                        <AlignLeft size={13} />
                                      </div>
                                    )}
                                  </div>

                                  <div className="badges-right">
                                    {ticket.assignee_id ? (
                                      (() => {
                                        const ass = memberOptions.find(m => m.user_id === ticket.assignee_id);
                                        return (
                                          <div 
                                            className="card-assignee-avatar" 
                                            style={{ backgroundColor: getAvatarColor(ass?.name || "Assignee") }}
                                            title={`Assigned to: ${ass?.name || "Member"}`}
                                          >
                                            {getInitials(ass?.name || "A")}
                                          </div>
                                        );
                                      })()
                                    ) : (
                                      <div className="card-assignee-avatar unassigned" title="Unassigned">
                                        -
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Add a Card inline footer */}
                      <div className="list-footer">
                        {addingTicketSectionId === section.id ? (
                          <div className="inline-add-card-form">
                            <textarea
                              placeholder="Enter a title for this ticket..."
                              value={newTicketName}
                              onChange={(e) => setNewTicketName(e.target.value)}
                              rows={2}
                              className="new-card-textarea"
                              onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                  e.preventDefault();
                                  createTicket(section.id);
                                }
                              }}
                              autoFocus
                            />
                            <div className="form-actions">
                              <button className="primary-btn-sm" onClick={() => createTicket(section.id)}>
                                Add ticket
                              </button>
                              <button className="close-btn-sm" onClick={() => { setAddingTicketSectionId(null); setNewTicketName(""); }}>
                                <X size={16} />
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button className="add-card-btn" onClick={() => setAddingTicketSectionId(section.id)}>
                            <Plus size={16} /> Add a ticket
                          </button>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Add Another List Section */}
                  <div className="kanban-list add-list-wrapper">
                    {addingSection ? (
                      <form className="inline-add-list-form" onSubmit={createSection}>
                        <input
                          type="text"
                          placeholder="Enter list title..."
                          value={newSectionName}
                          onChange={(e) => setNewSectionName(e.target.value)}
                          className="new-list-input"
                          autoFocus
                          required
                        />
                        <div className="form-actions">
                          <button type="submit" className="primary-btn-sm">Add list</button>
                          <button type="button" className="close-btn-sm" onClick={() => { setAddingSection(false); setNewSectionName(""); }}>
                            <X size={16} />
                          </button>
                        </div>
                      </form>
                    ) : (
                      <button className="add-list-btn" onClick={() => setAddingSection(true)}>
                        <Plus size={16} /> Add another list
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Card Details Modal Dialog */}
      {selectedTicket && (
        <CardDetailModal
          ticket={selectedTicket}
          sections={boardDetail?.sections || []}
          members={memberOptions}
          currentUser={user}
          isOwner={isOwner}
          onClose={() => setSelectedTicket(null)}
          onUpdateTicket={updateTicket}
          onDeleteTicket={deleteTicket}
          getAvatarColor={getAvatarColor}
          getInitials={getInitials}
        />
      )}

      {/* Create Board Modal */}
      {createBoardModalOpen && (
        <CreateBoardModal
          onClose={() => setCreateBoardModalOpen(false)}
          onCreateBoard={createBoard}
        />
      )}

      {/* Custom Confirm Modal popup */}
      {confirmModal && (
        <div className="modal-backdrop-confirm">
          <div className="confirm-modal-box">
            <h3>Are you sure?</h3>
            <p>{confirmModal.message}</p>
            <div className="confirm-actions">
              <button className="primary-btn danger" onClick={confirmModal.onConfirm}>
                Confirm Delete
              </button>
              <button className="secondary-btn" onClick={() => setConfirmModal(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Child Components

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

  const title = mode === "reset" ? "Reset password" : mode === "login" ? "Log in to Trello" : "Sign up for Trello";

  return (
    <main className="auth-layout">
      <div className="landing-container">

        {/* Top Branding */}
        <header className="landing-header">
          <div className="landing-logo">
            <LayoutDashboard size={32} className="landing-logo-icon" />
            <span>Trello</span>
          </div>
          <h1>Collaborate, manage, and reach new productivity peaks.</h1>
        </header>

        {/* Center Auth Card */}
        <div className="landing-center-box">
          <section className="auth-panel-premium">
            <div className="auth-header-trello">
              <h2>{title}</h2>
            </div>

            {mode !== "reset" && (
              <div className="segmented-auth">
                <button
                  className={mode === "login" ? "active" : ""}
                  onClick={() => setMode("login")}
                  type="button"
                >
                  Sign In
                </button>
                <button
                  className={mode === "register" ? "active" : ""}
                  onClick={() => setMode("register")}
                  type="button"
                >
                  Create Account
                </button>
              </div>
            )}

            <form className="stacked-form-premium" onSubmit={submit} autoComplete="off">
              {mode === "register" && (
                <div className="input-group">
                  <label htmlFor="name">Name</label>
                  <input id="name" name="name" placeholder="" required className="auth-input" autoComplete="off" />
                </div>
              )}
              <div className="input-group">
                <label htmlFor="email">Email address</label>
                <input id="email" name="email" placeholder="" type="email" required className="auth-input" autoComplete="off" />
              </div>
              <div className="input-group">
                <label htmlFor="password">{mode === "reset" ? "New password" : "Password"}</label>
                <input id="password" name="password" placeholder="" type="password" minLength="6" required className="auth-input" autoComplete="new-password" />
              </div>
              {mode === "reset" && (
                <div className="input-group">
                  <label htmlFor="confirm-password">Confirm new password</label>
                  <input id="confirm-password" name="confirm_password" placeholder="" type="password" minLength="6" required className="auth-input" autoComplete="new-password" />
                </div>
              )}
              <button type="submit" disabled={loading} className="auth-submit-btn">
                {loading ? "Authenticating..." : mode === "reset" ? "Reset password" : mode === "login" ? "Log In" : "Register"}
              </button>

              <div className="auth-links">
                {mode === "login" && (
                  <button className="link-btn" type="button" onClick={() => setMode("reset")}>
                    Forgot password?
                  </button>
                )}
                {mode === "reset" && (
                  <button className="link-btn" type="button" onClick={() => setMode("login")}>
                    Back to sign in
                  </button>
                )}
              </div>

              {message && <p className="success-banner">{message}</p>}
              {error && lastSubmittedMode === mode && <p className="error-banner">{error}</p>}
            </form>
          </section>
        </div>



        <footer className="landing-footer">
        </footer>

      </div>
    </main>
  );
}

function StatusBar({ loading, message, error }) {
  if (!loading && !message && !error) return null;
  return (
    <div className={`trello-status-bar ${error ? "error" : loading ? "loading" : "success"}`}>
      {loading ? (
        <span className="spinner-row">
          <RefreshCw size={14} className="spin" /> Syncing with Atlassian Cloud...
        </span>
      ) : (
        <span>{error || message}</span>
      )}
    </div>
  );
}

// Card Detail Dialog Modal
function CardDetailModal({
  ticket,
  sections,
  members,
  currentUser,
  isOwner,
  onClose,
  onUpdateTicket,
  onDeleteTicket,
  getAvatarColor,
  getInitials
}) {
  const [descEditing, setDescEditing] = useState(false);
  const [descValue, setDescValue] = useState(ticket.description || "");
  const [nameEditing, setNameEditing] = useState(false);
  const [nameValue, setNameValue] = useState(ticket.name);

  const canEdit = isOwner || ticket.creator_id === currentUser?.id;
  const creator = members.find((m) => m.user_id === ticket.creator_id);
  const assignee = members.find((m) => m.user_id === ticket.assignee_id);

  function handleSaveDesc() {
    onUpdateTicket(ticket, { description: descValue || null });
    setDescEditing(false);
  }

  function handleSaveName() {
    if (nameValue.trim() && nameValue !== ticket.name) {
      onUpdateTicket(ticket, { name: nameValue });
    }
    setNameEditing(false);
  }

  return (
    <div className="modal-backdrop-card">
      <div className="card-detail-modal-box">
        {/* Modal Header */}
        <header className="card-modal-header">
          <div className="header-icon-row">
            <LayoutDashboard size={20} className="modal-title-icon" />
            <div className="title-area">
              {nameEditing && canEdit ? (
                <input
                  type="text"
                  value={nameValue}
                  onChange={(e) => setNameValue(e.target.value)}
                  onBlur={handleSaveName}
                  onKeyDown={(e) => e.key === "Enter" && handleSaveName()}
                  className="modal-title-input"
                  autoFocus
                />
              ) : (
                <h2 onClick={() => { if (canEdit) setNameEditing(true); }}>
                  {ticket.name}
                </h2>
              )}
              <p className="subtitle-list">in list <strong>{ticket.section_name}</strong></p>
            </div>
          </div>
          <button className="close-modal-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </header>

        {/* Modal Main Grid */}
        <div className="card-modal-grid">
          {/* Left Main Content */}
          <div className="modal-left-pane">

            {/* Metadata (Creator & Assignee details) */}
            <section className="modal-meta-strip">
              <div className="meta-block">
                <h4>Created By</h4>
                <div className="user-pill">
                  <div
                    className="small-avatar"
                    style={{ backgroundColor: getAvatarColor(creator?.name || "Member") }}
                  >
                    {getInitials(creator?.name)}
                  </div>
                  <span>{creator?.name || "Workspace member"}</span>
                </div>
              </div>

              <div className="meta-block">
                <h4>Assignee</h4>
                {canEdit ? (
                  <select
                    className="assignee-select-premium"
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
                ) : (
                  <div className="user-pill">
                    {assignee ? (
                      <>
                        <div
                          className="small-avatar"
                          style={{ backgroundColor: getAvatarColor(assignee.name) }}
                        >
                          {getInitials(assignee.name)}
                        </div>
                        <span>{assignee.name}</span>
                      </>
                    ) : (
                      <span>Unassigned</span>
                    )}
                  </div>
                )}
              </div>
            </section>

            {/* Description editing */}
            <section className="modal-description-section">
              <div className="section-title-icon-row">
                <AlignLeft size={20} />
                <h3>Description</h3>
              </div>

              <div className="desc-content-area">
                {descEditing ? (
                  <div className="desc-editor">
                    <textarea
                      placeholder="Add a more detailed description..."
                      value={descValue}
                      onChange={(e) => setDescValue(e.target.value)}
                      rows={4}
                      className="desc-textarea"
                    />
                    <div className="desc-editor-actions">
                      <button className="primary-btn-sm" onClick={handleSaveDesc}>
                        Save
                      </button>
                      <button className="secondary-btn-sm" onClick={() => { setDescValue(ticket.description || ""); setDescEditing(false); }}>
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    className={`desc-view-box ${!ticket.description ? "empty" : ""}`}
                    onClick={() => { if (canEdit) setDescEditing(true); }}
                  >
                    {ticket.description ? (
                      <p>{ticket.description}</p>
                    ) : (
                      <p className="placeholder">Add a more detailed description...</p>
                    )}
                  </div>
                )}
              </div>
            </section>

            {/* Mock comments feed for visuals */}
            <section className="modal-activity-section">
              <div className="section-title-icon-row">
                <CheckSquare size={20} />
                <h3>Activity Feed</h3>
              </div>
              <div className="comment-box-mock">
                <div className="small-avatar" style={{ backgroundColor: getAvatarColor(currentUser?.name || "User") }}>
                  {getInitials(currentUser?.name)}
                </div>
                <input placeholder="Write a comment..." className="comment-input-mock" disabled />
              </div>
              <div className="activity-timeline">
                <div className="timeline-item">
                  <div className="timeline-dot"></div>
                  <p>
                    <strong>{creator?.name || "Member"}</strong> created this ticket.
                  </p>
                </div>
                {assignee && (
                  <div className="timeline-item">
                    <div className="timeline-dot bg-blue"></div>
                    <p>
                      Assigned to <strong>{assignee.name}</strong>.
                    </p>
                  </div>
                )}
              </div>
            </section>
          </div>

          {/* Right Action Side Panel */}
          <div className="modal-right-pane">
            <h4 className="side-title">Move Ticket</h4>
            {canEdit ? (
              <div className="actions-dropdown-container">
                <label className="select-label">List Destination</label>
                <select
                  className="section-move-select"
                  value={ticket.section_id}
                  onChange={(event) =>
                    onUpdateTicket(ticket, { section_id: Number(event.target.value) }, "Card moved lists")
                  }
                >
                  {sections.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <p className="no-perm-text">Members can only move tickets they created.</p>
            )}

            <div className="sidebar-actions-divider"></div>

            <h4 className="side-title">Ticket Actions</h4>
            {canEdit ? (
              <button className="modal-action-button danger" onClick={() => onDeleteTicket(ticket)}>
                <Trash2 size={14} /> Delete Ticket
              </button>
            ) : (
              <p className="no-perm-text">Insufficient permission to delete this ticket.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Create Board Custom Modal
function CreateBoardModal({ onClose, onCreateBoard }) {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    onCreateBoard(name, desc);
  }

  return (
    <div className="modal-backdrop-board">
      <div className="create-board-modal-box">
        <header className="board-modal-header">
          <h3>Create Board</h3>
          <button className="close-modal-btn" onClick={onClose}><X size={20} /></button>
        </header>
        <form className="board-create-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="new-board-title">Board Title <span className="req">*</span></label>
            <input
              id="new-board-title"
              type="text"
              placeholder="e.g. Capstone Roadmap"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="board-form-input"
              required
              autoFocus
            />
          </div>

          <div className="board-create-actions">
            <button type="submit" className="primary-btn board-submit">
              Create Workspace Board
            </button>
            <button type="button" className="secondary-btn" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default App;
