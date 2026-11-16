// Small helper around fetch. The login token is kept in memory and in sessionStorage.
let token = sessionStorage.getItem("rn_token") || "";
let name = sessionStorage.getItem("rn_name") || "";
let role = sessionStorage.getItem("rn_role") || "";

export function setSession(newToken, fullName = "", newRole = "") {
  token = newToken;
  name = fullName;
  role = newRole;
  if (newToken) {
    sessionStorage.setItem("rn_token", newToken);
    sessionStorage.setItem("rn_name", fullName);
    sessionStorage.setItem("rn_role", newRole);
  } else {
    sessionStorage.removeItem("rn_token");
    sessionStorage.removeItem("rn_name");
    sessionStorage.removeItem("rn_role");
    photoCache.clear();
  }
}

export function hasToken() {
  return Boolean(token);
}

export function userName() {
  return name;
}

export function userRole() {
  return role;
}

const UNREACHABLE = "Could not reach the server. Check that the backend is running, then try again.";

async function request(path, init) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { ...init.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    });
  } catch {
    throw new Error(UNREACHABLE);
  }
  if (res.status === 401 && path !== "/auth/login") {
    setSession("");
    throw new Error("Your session has ended. Sign in again.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status >= 500) throw new Error(UNREACHABLE);
    throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
  }
  return data;
}

// JSON request
export function api(path, { method = "GET", body } = {}) {
  return request(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
}

// Form request with an optional photo (used for observations and fixes).
// The browser sets the multipart Content-Type itself.
export function apiForm(path, fields, photo) {
  const form = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    if (value !== null && value !== undefined && value !== "") form.append(key, value);
  }
  if (photo) form.append("photo", photo, photo.name || "photo.jpg");
  return request(path, { method: "POST", headers: {}, body: form });
}

// Photos need the token too, so fetch each one once as a blob and reuse its object URL.
const photoCache = new Map();

export function photoUrl(key) {
  if (!photoCache.has(key)) {
    photoCache.set(
      key,
      fetch(`/api/inspections/photos/${key}`, { headers: { Authorization: `Bearer ${token}` } })
        .then((res) => (res.ok ? res.blob() : null))
        .then((blob) => (blob ? URL.createObjectURL(blob) : null))
        .catch(() => null)
    );
  }
  return photoCache.get(key);
}
