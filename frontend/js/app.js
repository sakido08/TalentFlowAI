// Talentflow AI uses plain browser JavaScript so the student workflow is easy to follow.
const TOKEN_KEY = "talentflow_token";
let currentUser = null;
let currentPage = "dashboard";
let editingJob = null;
let resumeForEditor = null;

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const initials = (name = "TF") => name.split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase();
const dateLabel = value => value ? new Date(value).toLocaleDateString(undefined, {year:"numeric",month:"short",day:"numeric"}) : "—";

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api${path}`, {...options, headers});
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && token) logout(false);
    throw new Error(data?.detail || "Something went wrong. Please try again.");
  }
  return data;
}

function authNotice(message, isError = false) {
  const box = $("#notice"); box.hidden = !message; box.textContent = message || ""; box.classList.toggle("error", isError);
}
function appNotice(message, isError = false) {
  const box = $("#app-notice"); box.hidden = !message; box.textContent = message || ""; box.classList.toggle("error", isError);
  if (message) setTimeout(() => { if (box.textContent === message) box.hidden = true; }, 5000);
}
function showAuth(register = false) {
  $("#auth-view").hidden = false; $("#app-view").hidden = true;
  $("#login-form").hidden = register; $("#register-form").hidden = !register;
  $("#auth-heading").textContent = register ? "Create your account" : "Welcome back";
  $("#auth-subtitle").textContent = register ? "Start exploring your career potential." : "Sign in to continue to your workspace.";
  $("#auth-switch-copy").textContent = register ? "Already have an account?" : "New to Talentflow AI?";
  $("#auth-switch").textContent = register ? "Log in" : "Create an account";
  authNotice("");
}
function showApp() {
  $("#auth-view").hidden = true; $("#app-view").hidden = false;
  $("#user-name").textContent = currentUser.name; $("#user-role").textContent = currentUser.role;
  $("#user-avatar").textContent = initials(currentUser.name);
  buildNav();
  const requested = location.hash.slice(1);
  currentPage = allowedPages().includes(requested) ? requested : "dashboard";
  renderPage();
}
const pageList = [
  {id:"dashboard", title:"Dashboard", icon:"⌂", roles:["user","recruiter","admin"]},
  {id:"upload", title:"Resume upload", icon:"↑", roles:["user","recruiter"]},
  {id:"resumes", title:"My resumes", icon:"▤", roles:["user"]},
  {id:"candidates", title:"Candidates", icon:"♙", roles:["recruiter","admin"]},
  {id:"jobs", title:"Jobs", icon:"▣", roles:["recruiter","admin"]},
  {id:"matching", title:"Matching", icon:"⌕", roles:["recruiter","admin"]},
  {id:"history", title:"History", icon:"◷", roles:["user","recruiter","admin"]},
  {id:"admin", title:"Admin panel", icon:"⚙", roles:["admin"]},
];
function allowedPages() { return pageList.filter(page => page.roles.includes(currentUser?.role)).map(page => page.id); }
function buildNav() {
  $("#nav-links").innerHTML = pageList.filter(page => page.roles.includes(currentUser.role)).map(page =>
    `<a href="#${page.id}" data-route="${page.id}" class="nav-link ${page.id === currentPage ? "active" : ""}"><span>${page.icon}</span>${page.title}</a>`).join("");
}
function navigate(page) {
  if (!allowedPages().includes(page)) return;
  currentPage = page; location.hash = page; buildNav(); renderPage();
}
function logout(showMessage = true) {
  localStorage.removeItem(TOKEN_KEY); currentUser = null;
  showAuth(false);
  if (showMessage) authNotice("You have been logged out.");
}

function statCard(label, value, icon) {
  return `<div class="stat-card"><span class="stat-icon">${icon}</span><div class="stat-label">${escapeHtml(label)}</div><div class="stat-value">${escapeHtml(value ?? 0)}</div></div>`;
}
function emptyState(title, description, button = "", route = "") {
  return `<div class="empty-state"><div class="empty-icon">✳</div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(description)}</p>${button ? `<button class="button primary" data-route="${route}">${escapeHtml(button)}</button>` : ""}</div>`;
}
function personCell(name, email) {
  return `<div class="person-cell"><span class="avatar">${escapeHtml(initials(name || "?"))}</span><div><strong>${escapeHtml(name || "Needs review")}</strong><small>${escapeHtml(email || "No email found")}</small></div></div>`;
}
function skillTags(skills = []) {
  return `<div class="tag-list">${skills.slice(0, 4).map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("")}${skills.length > 4 ? `<span class="tag">+${skills.length - 4}</span>` : ""}</div>`;
}
function statusPill(status) { return `<span class="status-pill ${escapeHtml(status)}">${escapeHtml(status)}</span>`; }
function resumeTable(rows, actions = true) {
  if (!rows.length) return emptyState("No resumes yet", "Upload a PDF or DOCX resume to see extracted candidate details here.", currentUser.role === "user" ? "Upload a resume" : "Upload resume", "upload");
  return `<div class="table-wrap"><table><thead><tr><th>Candidate</th><th>Skills</th><th>Status</th><th>Uploaded</th><th>Actions</th></tr></thead><tbody>${rows.map(row => {
    const candidate = row.candidate || row;
    return `<tr><td>${personCell(candidate.full_name, candidate.email)}</td><td>${skillTags(candidate.skills || [])}</td><td>${statusPill(row.status || "completed")}</td><td>${dateLabel(row.uploaded_at)}</td><td><div class="row-actions"><button class="button small" data-open-resume="${row.id || candidate.resume_id}">View</button>${row.status === "failed" ? `<button class="button small" data-reprocess="${row.id}">Retry</button>` : ""}</div></td></tr>`;
  }).join("")}</tbody></table></div>`;
}

async function renderDashboard() {
  const data = await api("/dashboard");
  if (data.role === "user") {
    return `<div class="page-intro"><div><h2>Your career workspace</h2><p>Upload a resume, review the extracted fields, and correct anything that needs attention.</p></div><button class="button primary" data-route="upload">＋ Upload resume</button></div><div class="stat-grid">${statCard("My resumes", data.my_resumes, "▤")}${statCard("Processed", data.processed_resumes, "✓")}${statCard("Recent uploads", (data.recent || []).length, "◷")}</div><div class="panel"><div class="panel-head"><div><h2>Recent resumes</h2><p>Your latest uploads and extraction results</p></div><button class="button subtle" data-route="resumes">View all</button></div>${resumeTable(data.recent || [])}</div>`;
  }
  if (data.role === "admin") {
    return `<div class="page-intro"><div><h2>System overview</h2><p>A quick view of accounts and resume processing across Talentflow AI.</p></div><button class="button primary" data-route="admin">Manage users</button></div><div class="stat-grid">${statCard("Total users", data.total_users, "♙")}${statCard("Recruiters", data.total_recruiters, "▣")}${statCard("Resumes", data.total_resumes, "▤")}${statCard("Candidates", data.total_candidates, "◉")}</div><div class="panel"><h2>Administrator workspace</h2><p class="muted">Manage roles and account access from the Admin panel. System events are recorded in the activity list.</p><div class="quick-actions"><button class="button" data-route="admin">Open admin panel</button><button class="button" data-route="history">View resume history</button></div></div>`;
  }
  return `<div class="page-intro"><div><h2>Recruiter overview</h2><p>Review candidates and compare their resumes with your open roles.</p></div><button class="button primary" data-route="jobs">＋ Create a job</button></div><div class="stat-grid">${statCard("Candidates", data.total_candidates, "♙")}${statCard("Resumes", data.total_resumes, "▤")}${statCard("Your jobs", data.total_jobs, "▣")}</div><div class="panel"><div class="panel-head"><div><h2>Recently added candidates</h2><p>Open a profile to review extracted details</p></div><button class="button subtle" data-route="candidates">All candidates</button></div>${data.recent?.length ? `<div class="table-wrap"><table><thead><tr><th>Candidate</th><th>Profile</th></tr></thead><tbody>${data.recent.map(person => `<tr><td>${personCell(person.full_name,person.email)}</td><td><button class="button small" data-open-candidate="${person.id}">View profile</button></td></tr>`).join("")}</tbody></table></div>` : emptyState("No candidates yet","Upload a resume to create the first candidate profile.","Upload resume","upload")}</div>`;
}

function renderUpload() {
  return `<div class="page-intro"><div><h2>Upload and process a resume</h2><p>Talentflow extracts selectable text, identifies common fields, and saves them for your review.</p></div></div><div class="panel"><div class="panel-head"><div><h2>Upload a resume</h2><p>Supported formats: PDF and DOCX · Maximum size: 10 MB</p></div></div><form id="upload-form"><label class="dropzone" id="dropzone"><span class="drop-icon">↑</span><strong id="file-name">Drop your resume here</strong><p>or choose a file from your device</p><input id="resume-file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required><button type="button" class="button" id="choose-file">Choose file</button><span class="file-hint">Your original file is stored locally by this prototype.</span></label><div class="toolbar" style="justify-content:flex-end;margin-top:14px"><button class="button primary" type="submit">Upload and extract</button></div></form></div><div class="panel"><div class="panel-head"><div><h2>Recent uploads</h2><p>Review results or retry a failed extraction</p></div></div><div id="upload-recent">Loading…</div></div>`;
}
async function loadUploadRecent() { const rows = await api("/resumes"); $("#upload-recent").innerHTML = resumeTable(rows.slice(0, 5)); }

async function renderResumes() {
  const rows = await api("/resumes");
  return `<div class="page-intro"><div><h2>My resumes</h2><p>Review and manage the resumes you have uploaded.</p></div><button class="button primary" data-route="upload">＋ Upload resume</button></div><div class="panel">${resumeTable(rows)}</div>`;
}
function educationMarkup(items = []) {
  const rows = items.length ? items : [{}];
  return rows.map((item, index) => `<div class="repeat-card education-row"><div class="repeat-title"><strong>Education ${index + 1}</strong><button type="button" class="button small danger remove-row">Remove</button></div><div class="repeat-fields"><label>Institution<input data-field="institution" value="${escapeHtml(item.institution)}"></label><label>Degree<input data-field="degree" value="${escapeHtml(item.degree)}"></label><label>Field of study<input data-field="field" value="${escapeHtml(item.field)}"></label><label>Start date<input data-field="start_date" value="${escapeHtml(item.start_date)}" placeholder="2022"></label><label>End date<input data-field="end_date" value="${escapeHtml(item.end_date)}" placeholder="2026"></label></div></div>`).join("");
}
function experienceMarkup(items = []) {
  const rows = items.length ? items : [{}];
  return rows.map((item, index) => `<div class="repeat-card experience-row"><div class="repeat-title"><strong>Experience ${index + 1}</strong><button type="button" class="button small danger remove-row">Remove</button></div><div class="repeat-fields"><label>Company<input data-field="company" value="${escapeHtml(item.company)}"></label><label>Position<input data-field="position" value="${escapeHtml(item.position)}"></label><label>Start date<input data-field="start_date" value="${escapeHtml(item.start_date)}"></label><label>End date<input data-field="end_date" value="${escapeHtml(item.end_date)}"></label><label class="span-two">Description<textarea data-field="description" rows="3">${escapeHtml(item.description)}</textarea></label></div></div>`).join("");
}
function editorForm(candidate) {
  candidate = candidate || {};
  return `<form id="candidate-editor" data-resume-id="${candidate.resume_id || ""}" data-candidate-id="${candidate.id || ""}">
    <section class="result-section"><div class="result-section-heading"><h3>Personal information</h3><p>Contact details identified from the resume</p></div><div class="editor-grid"><label>Full name<input name="full_name" value="${escapeHtml(candidate.full_name)}"></label><label>Email<input name="email" type="email" value="${escapeHtml(candidate.email)}"></label><label>Phone<input name="phone" value="${escapeHtml(candidate.phone)}"></label><label>Address<input name="address" value="${escapeHtml(candidate.address)}"></label></div></section>
    <section class="result-section"><div class="result-section-heading"><h3>Summary</h3><p>Resume summary or profile statement</p></div><label>Summary<textarea name="summary" rows="3">${escapeHtml(candidate.summary)}</textarea></label></section>
    <section class="result-section"><div class="result-section-heading"><h3>Skills</h3><p>Skills found using the project dictionary</p></div><label>Extracted skills <small>(separate with commas)</small><input name="skills" value="${escapeHtml((candidate.skills || []).join(", "))}"></label></section>
    <section class="result-section"><div class="result-section-heading with-action"><div><h3>Education</h3><p>Schools, degrees, and dates identified</p></div><button type="button" class="button small" id="add-education">＋ Add education</button></div><div id="education-list">${educationMarkup(candidate.education || [])}</div></section>
    <section class="result-section"><div class="result-section-heading with-action"><div><h3>Experience</h3><p>Roles, organizations, and descriptions identified</p></div><button type="button" class="button small" id="add-experience">＋ Add experience</button></div><div id="experience-list">${experienceMarkup(candidate.experience || [])}</div></section>
    <section class="result-section"><div class="result-section-heading"><h3>Certifications</h3><p>Certificates listed in the resume</p></div><label>Extracted certifications <small>(separate with commas)</small><input name="certifications" value="${escapeHtml((candidate.certifications || []).join(", "))}"></label></section>
    <div class="toolbar" style="justify-content:flex-end;margin-top:17px"><button class="button primary" type="submit">Save changes</button></div>
  </form>`;
}
async function openResume(resumeId) {
  try {
    const resume = await api(`/resumes/${resumeId}`); resumeForEditor = resume;
    currentPage = "result"; $("#page-heading").textContent = "Resume review";
    $("#page-content").innerHTML = `<div class="page-intro"><div><h2>${escapeHtml(resume.filename)}</h2><p>${statusPill(resume.status)} ${resume.processing_seconds == null ? "" : `· Processed in ${resume.processing_seconds}s`}</p></div><div class="toolbar"><button class="button" data-reprocess="${resume.id}">↻ Reprocess</button><button class="button danger" data-delete-resume="${resume.id}">Delete resume</button></div></div>${resume.error_message ? `<div class="notice error">${escapeHtml(resume.error_message)}</div>` : ""}<div class="resume-layout"><div class="panel"><div class="panel-head"><div><h2>Original extracted text</h2><p>Use this to check the parser's guesses</p></div></div><pre class="resume-text">${escapeHtml(resume.candidate?.extracted_text || "No text was extracted yet.")}</pre></div><div class="panel"><div class="panel-head"><div><h2>Structured information</h2><p>Correct fields before saving your review</p></div></div>${editorForm(resume.candidate)}</div></div>`;
    window.scrollTo({top:0,behavior:"smooth"});
  } catch (error) { appNotice(error.message, true); }
}
function readRepeatRows(selector) {
  return $$(selector).map(row => Object.fromEntries($$("[data-field]", row).map(input => [input.dataset.field, input.value.trim()])))
    .filter(item => Object.values(item).some(Boolean));
}

async function renderCandidates(search = "", skill = "", education = "", experience = "") {
  const query = new URLSearchParams();
  if (search) query.set("search", search); if (skill) query.set("skill", skill);
  if (education) query.set("education", education); if (experience) query.set("experience", experience);
  const params = query.size ? `?${query.toString()}` : "";
  const rows = await api(`/candidates${params}`);
  return `<div class="page-intro"><div><h2>Candidate directory</h2><p>Search profiles and review extracted resume details.</p></div><button class="button primary" data-route="upload">＋ Upload resume</button></div><div class="panel"><div class="panel-head"><div><h2>All candidates</h2><p>${rows.length} profile${rows.length === 1 ? "" : "s"}</p></div></div><form id="candidate-search" class="toolbar" style="margin-bottom:15px"><input name="search" placeholder="Name, email, resume" value="${escapeHtml(search)}"><input name="skill" placeholder="Filter skill" value="${escapeHtml(skill)}"><input name="education" placeholder="Filter education" value="${escapeHtml(education)}"><input name="experience" placeholder="Filter experience" value="${escapeHtml(experience)}"><button class="button" type="submit">Search</button></form>${rows.length ? `<div class="table-wrap"><table><thead><tr><th>Name</th><th>Skills</th><th>Education</th><th>Experience</th><th>Actions</th></tr></thead><tbody>${rows.map(person => `<tr><td>${personCell(person.full_name,person.email)}</td><td>${skillTags(person.skills)}</td><td>${escapeHtml(person.education?.[0]?.degree || "—")}<br><small>${escapeHtml(person.education?.[0]?.institution || "")}</small></td><td>${escapeHtml(person.experience?.[0]?.position || "—")}<br><small>${escapeHtml(person.experience?.[0]?.company || "")}</small></td><td><div class="row-actions"><button class="button small" data-open-resume="${person.resume_id}">View</button><button class="button small danger" data-delete-candidate="${person.id}">Delete</button></div></td></tr>`).join("")}</tbody></table></div>` : emptyState("No candidates found", "Try another search or upload a resume to add a candidate.", "Upload resume", "upload")}</div>`;
}
async function renderJobs() {
  const jobs = await api("/jobs");
  return `<div class="page-intro"><div><h2>Job descriptions</h2><p>Create roles with a description and a comma-separated skills list for matching.</p></div><button class="button primary" id="new-job">＋ Create job</button></div>${editingJob !== null ? jobForm(jobs.find(job => job.id === editingJob)) : ""}<div class="panel"><div class="panel-head"><div><h2>Your jobs</h2><p>${jobs.length} open description${jobs.length === 1 ? "" : "s"}</p></div></div>${jobs.length ? jobs.map(job => `<article class="job-card"><div class="job-card-head"><div><h3>${escapeHtml(job.title)}</h3><div class="tag-list">${job.required_skills.split(",").filter(Boolean).map(skill => `<span class="tag">${escapeHtml(skill.trim())}</span>`).join("")}</div></div><div class="row-actions"><button class="button small" data-edit-job="${job.id}">Edit</button><button class="button small danger" data-delete-job="${job.id}">Delete</button></div></div><p>${escapeHtml(job.description || "No description supplied.")}</p></article>`).join("") : emptyState("No jobs yet", "Create a job to compare candidates with a real description.", "Create a job")}</div>`;
}
function jobForm(job = null) {
  return `<div class="panel"><div class="panel-head"><div><h2>${job ? "Edit job" : "Create a job"}</h2><p>Use concise requirements to make the similarity score easier to interpret.</p></div></div><form id="job-form" data-id="${job?.id || ""}" class="inline-form"><label>Job title<input name="title" required value="${escapeHtml(job?.title || "")}"></label><label>Required skills <small>(comma-separated)</small><input name="required_skills" value="${escapeHtml(job?.required_skills || "")}" placeholder="Python, SQL, Git"></label><label class="span-two">Job description<textarea name="description" rows="5">${escapeHtml(job?.description || "")}</textarea></label><div class="toolbar span-two"><button class="button primary" type="submit">${job ? "Save job" : "Create job"}</button><button class="button" type="button" id="cancel-job">Cancel</button></div></form></div>`;
}
async function renderMatching() {
  const [candidates, jobs] = await Promise.all([api("/candidates"), api("/jobs")]);
  return `<div class="page-intro"><div><h2>Match a candidate to a job</h2><p>Compare a candidate profile and job using the project's weighted matching model.</p></div></div><div class="panel"><div class="panel-head"><div><h2>Choose a comparison</h2><p>The result combines skills, text similarity, and profile information for human review.</p></div></div>${candidates.length && jobs.length ? `<form id="matching-form" class="inline-form"><label>Candidate<select name="candidate_id" required><option value="">Select a candidate</option>${candidates.map(item => `<option value="${item.id}">${escapeHtml(item.full_name || item.email || `Candidate ${item.id}`)}</option>`).join("")}</select></label><label>Job<select name="job_id" required><option value="">Select a job</option>${jobs.map(job => `<option value="${job.id}">${escapeHtml(job.title)}</option>`).join("")}</select></label><div class="span-two"><button class="button primary" type="submit">Compare candidate</button></div></form><div id="match-result"></div>` : emptyState("A comparison needs a candidate and a job", "Upload a resume and create a job description before matching.", candidates.length ? "Create a job" : "Upload resume", candidates.length ? "jobs" : "upload")}</div><div class="panel"><h2>How to explain this score</h2><p class="muted">With SBERT off, the default is 55% TF-IDF, 30% required-skill coverage, 10% experience dates detected, and 5% education details detected. When SBERT is configured, semantic similarity gets 40% and TF-IDF gets 15%. Experience and education indicate that information was found; they do not measure qualification fit. This score is not a probability of being hired.</p></div>`;
}
async function renderHistory() {
  const rows = await api("/history");
  return `<div class="page-intro"><div><h2>Extraction history</h2><p>See upload status, processing time, and failed items that can be retried.</p></div></div><div class="panel">${rows.length ? `<div class="table-wrap"><table><thead><tr><th>Resume</th><th>Date</th><th>Status</th><th>Processing time</th><th>Action</th></tr></thead><tbody>${rows.map(item => `<tr><td>${escapeHtml(item.filename)}</td><td>${dateLabel(item.uploaded_at)}</td><td>${statusPill(item.status)}${item.error_message ? `<br><small>${escapeHtml(item.error_message)}</small>` : ""}</td><td>${item.processing_seconds == null ? "—" : `${item.processing_seconds}s`}</td><td><div class="row-actions"><button class="button small" data-open-resume="${item.id}">View</button>${item.status === "failed" ? `<button class="button small" data-reprocess="${item.id}">Retry</button>` : ""}</div></td></tr>`).join("")}</tbody></table></div>` : emptyState("No processing history", "Resume uploads and extraction results will appear here.", currentUser.role === "user" || currentUser.role === "recruiter" ? "Upload resume" : "", "upload")}</div>`;
}
async function renderAdmin() {
  const [users, activity, overview] = await Promise.all([api("/admin/users"), api("/admin/activity"), api("/admin/overview")]);
  return `<div class="page-intro"><div><h2>Admin panel</h2><p>Manage accounts, assign roles, and review recent system activity.</p></div></div><div class="stat-grid">${statCard("Users", overview.users, "♙")}${statCard("Recruiters", overview.recruiters, "▣")}${statCard("Resumes", overview.resumes, "▤")}${statCard("Candidates", overview.candidates, "◉")}</div><div class="panel"><div class="panel-head"><div><h2>Accounts</h2><p>New registrations are always assigned the User role.</p></div></div><div class="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Access</th><th>Actions</th></tr></thead><tbody>${users.map(person => `<tr><td>${escapeHtml(person.name)}</td><td>${escapeHtml(person.email)}</td><td><select data-role-user="${person.id}" aria-label="Role for ${escapeHtml(person.name)}"><option value="user" ${person.role === "user" ? "selected" : ""}>User</option><option value="recruiter" ${person.role === "recruiter" ? "selected" : ""}>Recruiter</option><option value="admin" ${person.role === "admin" ? "selected" : ""}>Admin</option></select></td><td>${person.is_active ? "Active" : "Disabled"}</td><td><div class="row-actions"><button class="button small" data-toggle-user="${person.id}" data-active="${person.is_active}">${person.is_active ? "Disable" : "Enable"}</button><button class="button small danger" data-delete-user="${person.id}">Delete</button></div></td></tr>`).join("")}</tbody></table></div></div><div class="panel"><div class="panel-head"><div><h2>Recent system activity</h2><p>Latest 100 recorded account and workflow events</p></div></div>${activity.length ? `<div class="table-wrap"><table><thead><tr><th>Event</th><th>Details</th><th>Date</th></tr></thead><tbody>${activity.map(item => `<tr><td>${escapeHtml(item.action)}</td><td>${escapeHtml(item.detail)}</td><td>${dateLabel(item.created_at)}</td></tr>`).join("")}</tbody></table></div>` : emptyState("No activity recorded", "New system events will appear here.")}</div>`;
}

async function renderPage() {
  if (!currentUser) return;
  if (currentPage === "result") { if (resumeForEditor) await openResume(resumeForEditor.id); return; }
  const page = pageList.find(item => item.id === currentPage);
  $("#page-heading").textContent = page?.title || "Dashboard";
  const content = $("#page-content"); content.innerHTML = `<div class="panel">Loading…</div>`;
  try {
    const output = currentPage === "dashboard" ? await renderDashboard()
      : currentPage === "upload" ? renderUpload()
      : currentPage === "resumes" ? await renderResumes()
      : currentPage === "candidates" ? await renderCandidates()
      : currentPage === "jobs" ? await renderJobs()
      : currentPage === "matching" ? await renderMatching()
      : currentPage === "history" ? await renderHistory()
      : currentPage === "admin" ? await renderAdmin() : "";
    content.innerHTML = output;
    if (currentPage === "upload") loadUploadRecent().catch(error => appNotice(error.message, true));
  } catch (error) {
    content.innerHTML = `<div class="panel">${emptyState("Could not load this page", error.message)}</div>`;
  }
}

async function submitCandidate(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  data.skills = data.skills.split(",").map(item => item.trim()).filter(Boolean);
  data.certifications = data.certifications.split(",").map(item => item.trim()).filter(Boolean);
  data.education = readRepeatRows(".education-row");
  data.experience = readRepeatRows(".experience-row");
  const path = form.dataset.resumeId ? `/resumes/${form.dataset.resumeId}` : `/candidates/${form.dataset.candidateId}`;
  await api(path, {method:"PUT", body:JSON.stringify(data)});
  appNotice("Candidate information saved.");
  if (currentPage === "result") await openResume(form.dataset.resumeId);
  else await renderPage();
}

document.addEventListener("click", async event => {
  const route = event.target.closest("[data-route]");
  if (route) { event.preventDefault(); navigate(route.dataset.route); return; }
  if (event.target.closest("#logout-button")) { logout(); return; }
  if (event.target.closest("#choose-file")) { event.preventDefault(); $("#resume-file")?.click(); return; }
  if (event.target.closest("#new-job")) { editingJob = "new"; await renderPage(); return; }
  if (event.target.closest("#cancel-job")) { editingJob = null; await renderPage(); return; }
  if (event.target.closest("#add-education")) { $("#education-list").insertAdjacentHTML("beforeend", educationMarkup([{}])); return; }
  if (event.target.closest("#add-experience")) { $("#experience-list").insertAdjacentHTML("beforeend", experienceMarkup([{}])); return; }
  if (event.target.closest(".remove-row")) { event.target.closest(".repeat-card").remove(); return; }
  const openResumeButton = event.target.closest("[data-open-resume]");
  if (openResumeButton) { await openResume(openResumeButton.dataset.openResume); return; }
  const openCandidateButton = event.target.closest("[data-open-candidate]");
  if (openCandidateButton) { const candidate = await api(`/candidates/${openCandidateButton.dataset.openCandidate}`); await openResume(candidate.resume_id); return; }
  const reprocessButton = event.target.closest("[data-reprocess]");
  if (reprocessButton) { const result = await api(`/resumes/${reprocessButton.dataset.reprocess}/extract`, {method:"POST"}); appNotice(result.status === "completed" ? "Resume reprocessed." : result.error_message, result.status !== "completed"); await openResume(result.id); return; }
  const deleteResume = event.target.closest("[data-delete-resume]");
  if (deleteResume && confirm("Delete this resume and its candidate profile?")) { await api(`/resumes/${deleteResume.dataset.deleteResume}`, {method:"DELETE"}); appNotice("Resume deleted."); navigate(currentUser.role === "user" ? "resumes" : "candidates"); return; }
  const deleteCandidate = event.target.closest("[data-delete-candidate]");
  if (deleteCandidate && confirm("Delete this candidate and their resume?")) { await api(`/candidates/${deleteCandidate.dataset.deleteCandidate}`, {method:"DELETE"}); appNotice("Candidate deleted."); await renderPage(); return; }
  const editJob = event.target.closest("[data-edit-job]");
  if (editJob) { editingJob = Number(editJob.dataset.editJob); await renderPage(); return; }
  const deleteJob = event.target.closest("[data-delete-job]");
  if (deleteJob && confirm("Delete this job description?")) { await api(`/jobs/${deleteJob.dataset.deleteJob}`, {method:"DELETE"}); appNotice("Job deleted."); await renderPage(); return; }
  const toggleUser = event.target.closest("[data-toggle-user]");
  if (toggleUser) { const isActive = toggleUser.dataset.active !== "true"; await api(`/admin/users/${toggleUser.dataset.toggleUser}/active`, {method:"PUT",body:JSON.stringify({is_active:isActive})}); appNotice(`Account ${isActive ? "enabled" : "disabled"}.`); await renderPage(); return; }
  const deleteUser = event.target.closest("[data-delete-user]");
  if (deleteUser && confirm("Delete this user and their uploaded records?")) { await api(`/admin/users/${deleteUser.dataset.deleteUser}`, {method:"DELETE"}); appNotice("User deleted."); await renderPage(); }
});

document.addEventListener("change", async event => {
  const roleSelect = event.target.closest("[data-role-user]");
  if (roleSelect) {
    try { await api(`/admin/users/${roleSelect.dataset.roleUser}/role`, {method:"PUT",body:JSON.stringify({role:roleSelect.value})}); appNotice("User role updated."); }
    catch (error) { appNotice(error.message, true); await renderPage(); }
  }
  if (event.target.id === "resume-file") $("#file-name").textContent = event.target.files[0]?.name || "Drop your resume here";
});

document.addEventListener("submit", async event => {
  const form = event.target;
  if (["login-form", "register-form"].includes(form.id)) return;
  event.preventDefault();
  try {
    if (form.id === "upload-form") {
      const file = $("#resume-file").files[0]; if (!file) throw new Error("Choose a PDF or DOCX resume first.");
      const body = new FormData(); body.append("file", file);
      const result = await api("/resumes/upload", {method:"POST",body});
      appNotice(result.status === "completed" ? "Resume uploaded and extracted. Review the results below." : result.error_message, result.status !== "completed");
      await openResume(result.id); return;
    }
    if (form.id === "candidate-editor") { await submitCandidate(form); return; }
    if (form.id === "candidate-search") { const values = new FormData(form); $("#page-content").innerHTML = await renderCandidates(values.get("search"), values.get("skill"), values.get("education"), values.get("experience")); return; }
    if (form.id === "job-form") {
      const data = Object.fromEntries(new FormData(form).entries());
      await api(form.dataset.id ? `/jobs/${form.dataset.id}` : "/jobs", {method:form.dataset.id ? "PUT" : "POST",body:JSON.stringify(data)});
      editingJob = null; appNotice(form.dataset.id ? "Job updated." : "Job created."); await renderPage(); return;
    }
    if (form.id === "matching-form") {
      const result = await api("/matching", {method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(form).entries()))});
      const list = (items, empty) => items.length ? `<div class="tag-list">${items.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>` : `<small>${empty}</small>`;
      const breakdown = result.components.map(component => `<div class="component-row"><div class="component-heading"><strong>${escapeHtml(component.label)}</strong><span>${component.score}% score · ${component.weight}% weight</span></div><div class="component-track"><span style="width:${component.score}%"></span></div><small>${component.contribution}% added to the overall score</small></div>`).join("");
      const modelMode = result.semantic_error ? "SBERT unavailable · default weights used" : result.semantic_score === null ? "Default model · SBERT off" : "SBERT semantic model enabled";
      $("#match-result").innerHTML = `<div class="match-result"><div class="match-result-top"><div><div class="eyebrow">WEIGHTED MATCH SCORE</div><div class="match-score">${result.overall_score}%</div><div class="score-note">Decision support for human review; not a hiring prediction.</div></div><span class="tag">${modelMode}</span></div>${result.semantic_error ? `<p class="score-note">${escapeHtml(result.semantic_error)}</p>` : ""}<div class="breakdown-list">${breakdown}</div><p class="formula-note"><strong>Formula:</strong> ${escapeHtml(result.formula)}</p><div class="skill-columns"><div class="skill-box"><h3>Matched skills</h3>${list(result.matched_skills,"No required skills were matched.")}</div><div class="skill-box"><h3>Missing skills</h3>${list(result.missing_skills,"No listed skills are missing.")}</div></div><p class="score-note" style="margin:13px 0 0">Experience and education signals indicate whether details were detected; they do not measure fit or qualification.</p><p class="score-note" style="margin:7px 0 0">${escapeHtml(result.notice)}</p></div>`;
    }
  } catch (error) { appNotice(error.message, true); }
});

document.addEventListener("dragover", event => { if (event.target.closest("#dropzone")) { event.preventDefault(); $("#dropzone").classList.add("drag"); } });
document.addEventListener("dragleave", event => { if (event.target.closest("#dropzone")) $("#dropzone").classList.remove("drag"); });
document.addEventListener("drop", event => {
  const zone = event.target.closest("#dropzone"); if (!zone) return;
  event.preventDefault(); zone.classList.remove("drag");
  const file = event.dataTransfer.files[0];
  if (file) { const transfer = new DataTransfer(); transfer.items.add(file); $("#resume-file").files = transfer.files; $("#file-name").textContent = file.name; }
});
window.addEventListener("hashchange", () => { const page = location.hash.slice(1); if (allowedPages().includes(page)) navigate(page); });

$("#auth-switch").addEventListener("click", () => showAuth(!$("#register-form").hidden));
$("#login-form").addEventListener("submit", async event => {
  event.preventDefault(); authNotice("");
  try {
    const values = Object.fromEntries(new FormData(event.target).entries());
    const result = await fetch("/api/login", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(values)}).then(async response => {const data=await response.json();if(!response.ok)throw new Error(data.detail);return data;});
    localStorage.setItem(TOKEN_KEY, result.access_token); currentUser = result.user; showApp();
  } catch (error) { authNotice(error.message || "Invalid email or password.", true); }
});
$("#register-form").addEventListener("submit", async event => {
  event.preventDefault(); authNotice("");
  const values = Object.fromEntries(new FormData(event.target).entries());
  if (values.password !== values.confirm_password) { authNotice("Passwords do not match.", true); return; }
  delete values.confirm_password;
  try { await fetch("/api/register", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(values)}).then(async response => {const data=await response.json();if(!response.ok)throw new Error(data.detail);return data;}); showAuth(false); authNotice("Account created. You can now log in."); }
  catch (error) { authNotice(error.message, true); }
});

async function initialize() {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) { showAuth(false); return; }
  try { currentUser = await api("/me"); showApp(); }
  catch { localStorage.removeItem(TOKEN_KEY); showAuth(false); }
}
initialize();
