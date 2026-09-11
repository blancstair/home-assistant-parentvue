/*
 * ParentVUE Dashboard Card
 * Bundled with the ParentVUE Home Assistant integration.
 *
 * No external JavaScript dependencies.
 * Discovers ParentVUE entities through Home Assistant's entity/device registries.
 */

const CARD_NAME = "parentvue-dashboard-card";
const INTEGRATION_DOMAIN = "parentvue";

class ParentVueDashboardCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = {};
    this._entries = [];
    this._devices = new Map();
    this._loadingRegistry = false;
    this._registryLoaded = false;
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._registryLoaded && !this._loadingRegistry) {
      this._loadRegistry();
    } else {
      this._render();
    }
  }

  getCardSize() {
    const deviceIds = new Set(this._entries.map((entry) => entry.device_id).filter(Boolean));
    return Math.max(3, deviceIds.size * 4);
  }

  async _loadRegistry() {
    if (!this._hass || this._loadingRegistry) return;

    this._loadingRegistry = true;
    try {
      const [entities, devices] = await Promise.all([
        this._hass.callWS({ type: "config/entity_registry/list" }),
        this._hass.callWS({ type: "config/device_registry/list" }),
      ]);

      this._entries = (entities || []).filter(
        (entry) =>
          entry.platform === INTEGRATION_DOMAIN ||
          entry.entity_id?.startsWith("sensor.parentvue_")
      );

      this._devices = new Map(
        (devices || []).map((device) => [device.id, device])
      );

      this._registryLoaded = true;
    } catch (err) {
      // Do not expose registry contents or other private state in console logs.
      console.warn("ParentVUE dashboard card could not load Home Assistant registries.");
    } finally {
      this._loadingRegistry = false;
      this._render();
    }
  }

  _state(entry) {
    return this._hass?.states?.[entry.entity_id] || null;
  }

  _friendlyName(entry) {
    const state = this._state(entry);
    return state?.attributes?.friendly_name || entry.name || entry.original_name || entry.entity_id;
  }

  _uniqueId(entry) {
    return String(entry.unique_id || "");
  }

  _classify(entry) {
    const uid = this._uniqueId(entry);
    if (uid.endsWith("_school")) return "school";
    if (uid.endsWith("_grade_level")) return "grade_level";
    if (uid.endsWith("_missing_assignments")) return "missing";
    if (uid.endsWith("_current_class")) return "current_class";
    if (uid.endsWith("_next_class")) return "next_class";
    if (uid.includes("_course_") && uid.endsWith("_grade")) return "course";
    return "other";
  }

  _formatState(entry) {
    const state = this._state(entry);
    if (!state) return "Unavailable";
    if (state.state === "unknown") return "Unknown";
    if (state.state === "unavailable") return "Unavailable";
    const unit = state.attributes?.unit_of_measurement;
    return unit ? `${state.state} ${unit}` : state.state;
  }

  _deviceName(deviceId, entries) {
    const device = this._devices.get(deviceId);
    if (device?.name_by_user) return device.name_by_user;
    if (device?.name) return device.name;

    for (const entry of entries) {
      const state = this._state(entry);
      const friendly = state?.attributes?.friendly_name;
      if (friendly) {
        return friendly.replace(/\s+(School|Grade level|Missing assignments|Current class|Next class)$/i, "");
      }
    }
    return "ParentVUE student";
  }

  _moreInfo(entityId) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        bubbles: true,
        composed: true,
        detail: { entityId },
      })
    );
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _metric(label, entry, icon = "") {
    if (!entry) {
      return `
        <div class="metric disabled">
          <div class="metric-label">${this._escape(label)}</div>
          <div class="metric-value">Not available</div>
        </div>
      `;
    }

    const entityId = this._escape(entry.entity_id);
    return `
      <button class="metric" data-entity="${entityId}">
        <div class="metric-label">${this._escape(label)}</div>
        <div class="metric-value">${this._escape(this._formatState(entry))}</div>
      </button>
    `;
  }

  _courseRow(entry) {
    const state = this._state(entry);
    const attrs = state?.attributes || {};
    const name = attrs.course_name || this._friendlyName(entry).replace(/\s+grade$/i, "");
    const missing = attrs.missing_assignments;
    const secondary = [
      attrs.period ? `Period ${attrs.period}` : null,
      attrs.teacher || null,
      missing != null ? `${missing} missing` : null,
    ].filter(Boolean).join(" · ");

    return `
      <button class="course" data-entity="${this._escape(entry.entity_id)}">
        <div class="course-copy">
          <div class="course-name">${this._escape(name)}</div>
          ${secondary ? `<div class="course-secondary">${this._escape(secondary)}</div>` : ""}
        </div>
        <div class="course-grade">${this._escape(this._formatState(entry))}</div>
      </button>
    `;
  }

  _studentCard(deviceId, entries) {
    const byType = {};
    const courses = [];

    for (const entry of entries) {
      const type = this._classify(entry);
      if (type === "course") {
        courses.push(entry);
      } else if (!byType[type]) {
        byType[type] = entry;
      }
    }

    courses.sort((a, b) => {
      const aName = this._state(a)?.attributes?.course_name || this._friendlyName(a);
      const bName = this._state(b)?.attributes?.course_name || this._friendlyName(b);
      return String(aName).localeCompare(String(bName));
    });

    const studentName = this._deviceName(deviceId, entries);
    const school = byType.school ? this._formatState(byType.school) : "";
    const grade = byType.grade_level ? this._formatState(byType.grade_level) : "";
    const subtitle = [grade, school].filter((x) => x && x !== "Unknown" && x !== "Unavailable").join(" · ");

    return `
      <section class="student">
        <header class="student-header">
          <div>
            <h2>${this._escape(studentName)}</h2>
            ${subtitle ? `<div class="subtitle">${this._escape(subtitle)}</div>` : ""}
          </div>
        </header>

        <div class="metrics">
          ${this._metric("Missing assignments", byType.missing)}
          ${this._metric("Current class", byType.current_class)}
          ${this._metric("Next class", byType.next_class)}
        </div>

        <div class="section-title">Courses</div>
        <div class="courses">
          ${
            courses.length
              ? courses.map((entry) => this._courseRow(entry)).join("")
              : `<div class="empty">No course entities are available yet.</div>`
          }
        </div>
      </section>
    `;
  }

  _bindClicks() {
    this.shadowRoot.querySelectorAll("[data-entity]").forEach((element) => {
      element.addEventListener("click", () => {
        const entityId = element.getAttribute("data-entity");
        if (entityId) this._moreInfo(entityId);
      });
    });
  }

  _render() {
    if (!this.shadowRoot) return;

    const styles = `
      <style>
        :host {
          display: block;
          --pv-gap: 14px;
        }
        ha-card, .card {
          display: block;
          background: var(--ha-card-background, var(--card-background-color));
          color: var(--primary-text-color);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow);
          border: var(--ha-card-border-width, 0) solid var(--ha-card-border-color, transparent);
          padding: 16px;
        }
        .title {
          font-size: 22px;
          font-weight: 600;
          margin: 0 0 16px;
        }
        .student {
          border-top: 1px solid var(--divider-color);
          padding-top: 18px;
          margin-top: 18px;
        }
        .student:first-of-type {
          border-top: 0;
          padding-top: 0;
          margin-top: 0;
        }
        .student-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 14px;
        }
        h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
        }
        .subtitle {
          margin-top: 4px;
          color: var(--secondary-text-color);
          font-size: 14px;
        }
        .metrics {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
          margin-bottom: 18px;
        }
        button {
          font: inherit;
          color: inherit;
        }
        .metric, .course {
          border: 0;
          text-align: left;
          background: var(--secondary-background-color);
          border-radius: 10px;
          cursor: pointer;
        }
        .metric {
          min-height: 82px;
          padding: 12px;
        }
        .metric:hover, .course:hover {
          background: color-mix(in srgb, var(--secondary-background-color) 88%, var(--primary-color));
        }
        .metric.disabled {
          cursor: default;
          opacity: 0.65;
        }
        .metric-label {
          color: var(--secondary-text-color);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: .04em;
        }
        .metric-value {
          margin-top: 8px;
          font-size: 17px;
          font-weight: 600;
          overflow-wrap: anywhere;
        }
        .section-title {
          margin: 4px 0 8px;
          font-size: 14px;
          font-weight: 600;
          color: var(--secondary-text-color);
        }
        .courses {
          display: grid;
          gap: 8px;
        }
        .course {
          width: 100%;
          padding: 12px 14px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
        }
        .course-copy {
          min-width: 0;
        }
        .course-name {
          font-weight: 500;
          overflow-wrap: anywhere;
        }
        .course-secondary {
          color: var(--secondary-text-color);
          font-size: 12px;
          margin-top: 3px;
          overflow-wrap: anywhere;
        }
        .course-grade {
          flex: 0 0 auto;
          font-size: 18px;
          font-weight: 700;
        }
        .empty, .loading {
          color: var(--secondary-text-color);
          padding: 12px 0;
        }
        @media (max-width: 650px) {
          .metrics {
            grid-template-columns: 1fr;
          }
        }
      </style>
    `;

    if (!this._hass) {
      this.shadowRoot.innerHTML = `${styles}<ha-card><div class="loading">Waiting for Home Assistant…</div></ha-card>`;
      return;
    }

    if (!this._registryLoaded) {
      this.shadowRoot.innerHTML = `${styles}<ha-card><div class="loading">Loading ParentVUE dashboard…</div></ha-card>`;
      return;
    }

    const groups = new Map();
    for (const entry of this._entries) {
      const key = entry.device_id || "unassigned";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(entry);
    }

    const title = this._config.title === false ? "" : (this._config.title || "ParentVUE");

    const content = groups.size
      ? [...groups.entries()]
          .sort(([a], [b]) => this._deviceName(a, groups.get(a)).localeCompare(this._deviceName(b, groups.get(b))))
          .map(([deviceId, entries]) => this._studentCard(deviceId, entries))
          .join("")
      : `<div class="empty">No ParentVUE entities were found. Confirm the ParentVUE integration is configured and loaded.</div>`;

    this.shadowRoot.innerHTML = `
      ${styles}
      <ha-card>
        <div class="card">
          ${title ? `<div class="title">${this._escape(title)}</div>` : ""}
          ${content}
        </div>
      </ha-card>
    `;

    this._bindClicks();
  }
}

if (!customElements.get(CARD_NAME)) {
  customElements.define(CARD_NAME, ParentVueDashboardCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_NAME)) {
  window.customCards.push({
    type: CARD_NAME,
    name: "ParentVUE Dashboard",
    description: "Automatic dashboard for ParentVUE students, classes, and grades.",
    preview: true,
  });
}
