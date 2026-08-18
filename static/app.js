const state = { data: null, club: "", age: "", season: "" };

function fmtDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function populateSelect(id, values, current) {
  const sel = document.getElementById(id);
  sel.innerHTML = '<option value="">הכל</option>' +
    values.map(v => `<option value="${v}" ${v === current ? "selected" : ""}>${v}</option>`).join("");
}

function rowUpcoming(g) {
  return `<tr>
    <td>${fmtDate(g.date)}</td>
    <td>${g.time || ""}</td>
    <td>${g.club_name || ""}</td>
    <td>${g.age_group || ""}</td>
    <td>${g.home_team || ""}</td>
    <td>${g.away_team || ""}</td>
    <td>${g.season_label || ""}</td>
  </tr>`;
}

function rowArchive(g) {
  const score = (g.home_score != null && g.away_score != null) ? `${g.home_score} - ${g.away_score}` : "";
  return `<tr>
    <td>${fmtDate(g.date)}</td>
    <td>${g.time || ""}</td>
    <td>${g.club_name || ""}</td>
    <td>${g.age_group || ""}</td>
    <td>${g.home_team || ""}</td>
    <td>${score}</td>
    <td>${g.away_team || ""}</td>
    <td>${g.season_label || ""}</td>
  </tr>`;
}

async function loadGames() {
  const params = new URLSearchParams();
  if (state.club) params.set("club", state.club);
  if (state.age) params.set("age_group", state.age);
  if (state.season) params.set("season", state.season);

  const res = await fetch(`/api/games?${params.toString()}`);
  const data = await res.json();
  state.data = data;

  document.getElementById("updated-at").textContent = data.updated_at
    ? `עודכן לאחרונה: ${new Date(data.updated_at).toLocaleString("he-IL")}`
    : "טרם עודכן — לחצו על עדכון נתונים";

  populateSelect("filter-club", data.filters.clubs, state.club ? findClubName(data) : "");
  populateSelect("filter-age", data.filters.age_groups, state.age);
  populateSelect("filter-season", data.filters.seasons, state.season);

  const upcomingBody = document.getElementById("upcoming-body");
  const archiveBody = document.getElementById("archive-body");
  upcomingBody.innerHTML = data.upcoming.map(rowUpcoming).join("");
  archiveBody.innerHTML = data.archive.map(rowArchive).join("");

  document.getElementById("upcoming-empty").hidden = data.upcoming.length > 0;
  document.getElementById("archive-empty").hidden = data.archive.length > 0;
}

function findClubName(data) {
  for (const [name, key] of Object.entries(data.filters.club_keys)) {
    if (key === state.club) return name;
  }
  return "";
}

document.getElementById("filter-club").addEventListener("change", e => {
  const name = e.target.value;
  const key = state.data ? state.data.filters.club_keys[name] : "";
  state.club = key || "";
  loadGames();
});
document.getElementById("filter-age").addEventListener("change", e => { state.age = e.target.value; loadGames(); });
document.getElementById("filter-season").addEventListener("change", e => { state.season = e.target.value; loadGames(); });

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

const refreshBtn = document.getElementById("refresh-btn");
const refreshStatus = document.getElementById("refresh-status");

async function pollRefresh() {
  const res = await fetch("/api/refresh/status");
  const s = await res.json();
  if (s.running) {
    refreshStatus.textContent = "מעדכן... (יכול לקחת מספר דקות)";
    setTimeout(pollRefresh, 3000);
  } else {
    refreshBtn.disabled = false;
    if (s.last_result) {
      refreshStatus.textContent = s.last_result.ok ? "עודכן בהצלחה" : "העדכון נכשל — ראו קונסולה";
      if (!s.last_result.ok) console.error(s.last_result.stderr);
    }
    loadGames();
  }
}

refreshBtn.addEventListener("click", async () => {
  refreshBtn.disabled = true;
  refreshStatus.textContent = "מתחיל עדכון...";
  const res = await fetch("/api/refresh", { method: "POST" });
  if (res.status === 409) {
    refreshStatus.textContent = "עדכון כבר רץ...";
  }
  pollRefresh();
});

loadGames();
