/*
 * ParentVUE Dashboard Card
 * Bundled with the ParentVUE Home Assistant integration.
 *
 * No external JavaScript dependencies.
 * The card only reads Home Assistant entity/device registries and entity state.
 * It never contacts ParentVUE directly.
 */

const CARD_NAME = "parentvue-dashboard-card";
const EDITOR_NAME = "parentvue-dashboard-card-editor";
const INTEGRATION_DOMAIN = "parentvue";

const DEFAULTS = Object.freeze({
  show_school: true,
  show_grade_level: true,
  show_missing_assignments: true,
  missing_assignment_threshold: 1,
  missing_assignment_alert_color: "#c62828",
  show_current_class: true,
  show_next_class: true,
  show_today_schedule: true,
  schedule_show_period: true,
  schedule_show_teacher: true,
  schedule_show_room: true,
  schedule_show_times: true,
  schedule_show_delivery: true,
  schedule_highlight_current: true,
  show_courses: true,
  show_letter_grade: true,
  show_grade_percentage: true,
  show_course_period: true,
  show_course_teacher: true,
  show_course_room: true,
  show_marking_period: true,
  show_course_missing: true,
  show_course_delivery: true,
  show_attendance_today: true,
  show_attendance_year: true,
  show_synergy_mail: true,
});

const BOOLEAN_FIELDS = [
  ["Student", "show_school", "School"],
  ["Student", "show_grade_level", "Grade level"],
  ["Assignments", "show_missing_assignments", "Missing assignments"],
  ["Schedule", "show_current_class", "Current class"],
  ["Schedule", "show_next_class", "Next class"],
  ["Schedule", "show_today_schedule", "Today's full schedule"],
  ["Schedule details", "schedule_show_period", "Period"],
  ["Schedule details", "schedule_show_teacher", "Teacher"],
  ["Schedule details", "schedule_show_room", "Room"],
  ["Schedule details", "schedule_show_times", "Start/end times"],
  ["Schedule details", "schedule_show_delivery", "Online / in-person"],
  ["Schedule details", "schedule_highlight_current", "Highlight current class"],
  ["Courses", "show_courses", "Course grades"],
  ["Course details", "show_letter_grade", "Letter grade"],
  ["Course details", "show_grade_percentage", "Grade percentage"],
  ["Course details", "show_course_period", "Period"],
  ["Course details", "show_course_teacher", "Teacher"],
  ["Course details", "show_course_room", "Room"],
  ["Course details", "show_marking_period", "Marking period"],
  ["Course details", "show_course_missing", "Missing assignments"],
  ["Course details", "show_course_delivery", "Online / in-person"],
  ["Attendance & mail", "show_attendance_today", "Today's attendance"],
  ["Attendance & mail", "show_attendance_year", "School-year attendance"],
  ["Attendance & mail", "show_synergy_mail", "Unread Synergy Mail"],
];

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
    return { ...DEFAULTS };
  }

  static getConfigElement() {
    return document.createElement(EDITOR_NAME);
  }

  setConfig(config) {
    this._config = { ...(config || {}) };
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
    const selected = this._selectedGroups();
    return Math.max(3, selected.length * 6);
  }

  _value(key) {
    return Object.prototype.hasOwnProperty.call(this._config, key)
      ? this._config[key]
      : DEFAULTS[key];
  }

  _flag(key) {
    return Boolean(this._value(key));
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
        (entry) => entry.platform === INTEGRATION_DOMAIN
      );

      this._devices = new Map(
        (devices || []).map((device) => [device.id, device])
      );

      this._registryLoaded = true;
    } catch (err) {
      console.warn("ParentVUE dashboard card could not load Home Assistant registries.");
    } finally {
      this._loadingRegistry = false;
      this._render();
    }
  }

  _state(entry) {
    return this._hass?.states?.[entry?.entity_id] || null;
  }

  _friendlyName(entry) {
    const state = this._state(entry);
    return state?.attributes?.friendly_name || entry?.name || entry?.original_name || entry?.entity_id || "";
  }

  _uniqueId(entry) {
    return String(entry?.unique_id || "");
  }

  _classify(entry) {
    const uid = this._uniqueId(entry);

    if (uid.endsWith("_student_name")) return { kind: "student_name" };
    if (uid.endsWith("_school")) return { kind: "school" };
    if (uid.endsWith("_grade_level")) return { kind: "grade_level" };
    if (uid.endsWith("_missing_assignments") && !uid.includes("_course_")) {
      return { kind: "missing" };
    }
    if (uid.endsWith("_today_schedule")) return { kind: "today_schedule" };
    if (uid.endsWith("_current_class")) return { kind: "current_class" };
    if (uid.endsWith("_next_class")) return { kind: "next_class" };
    if (uid.endsWith("_attendance_today")) return { kind: "attendance_today" };
    if (uid.endsWith("_attendance_year")) return { kind: "attendance_year" };
    if (uid.endsWith("_synergy_mail_unread")) return { kind: "synergy_mail" };

    const meetingMatch = uid.match(
      /_(current|next)_class_(period|teacher|room|start|end|delivery)$/
    );
    if (meetingMatch) {
      return {
        kind: `${meetingMatch[1]}_field`,
        field: meetingMatch[2],
      };
    }

    const courseMatch = uid.match(
      /_course_([0-9a-f]+)_(name|grade|percentage|teacher|room|period|marking_period|missing_assignments|delivery|last_updated)$/
    );
    if (courseMatch) {
      return {
        kind: "course",
        courseKey: courseMatch[1],
        field: courseMatch[2],
      };
    }

    return { kind: "other" };
  }

  _formatState(entry) {
    const state = this._state(entry);
    if (!state) return "Unavailable";
    if (state.state === "unknown") return "Unknown";
    if (state.state === "unavailable") return "Unavailable";
    const unit = state.attributes?.unit_of_measurement;
    return unit ? `${state.state} ${unit}` : state.state;
  }

  _usableState(entry) {
    const state = this._state(entry);
    if (!state || state.state === "unknown" || state.state === "unavailable") return "";
    return state.state;
  }

  _deviceName(deviceId, entries) {
    const device = this._devices.get(deviceId);
    if (device?.name_by_user) return device.name_by_user;
    if (device?.name) return device.name;

    for (const entry of entries) {
      const state = this._state(entry);
      const friendly = state?.attributes?.friendly_name;
      if (friendly) {
        return friendly.replace(
          /\s+(School|Grade level|Missing assignments|Today's schedule|Current class|Next class)$/i,
          ""
        );
      }
    }
    return "ParentVUE student";
  }

  _groups() {
    const groups = new Map();
    for (const entry of this._entries) {
      if (!entry.device_id) continue;
      const key = entry.device_id;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(entry);
    }
    return groups;
  }

  _globalEntry(kind) {
    return this._entries.find(
      (entry) => !entry.device_id && this._classify(entry).kind === kind
    ) || null;
  }

  _selectedGroups() {
    const groups = this._groups();
    const selectedDevice = String(this._config.child_device_id || "");
    let rows = [...groups.entries()];

    if (selectedDevice) {
      rows = rows.filter(([deviceId]) => deviceId === selectedDevice);
    }

    return rows.sort(([a], [b]) =>
      this._deviceName(a, groups.get(a)).localeCompare(
        this._deviceName(b, groups.get(b))
      )
    );
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

  _numberState(entry) {
    const raw = this._usableState(entry);
    if (raw === "") return null;
    const value = Number(raw);
    return Number.isFinite(value) ? value : null;
  }

  _alertColor() {
    const raw = String(this._value("missing_assignment_alert_color") || "");
    return /^#[0-9a-f]{6}$/i.test(raw) ? raw : DEFAULTS.missing_assignment_alert_color;
  }

  _contrastText(hex) {
    const normalized = hex.replace("#", "");
    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.58 ? "#111111" : "#ffffff";
  }

  _metric(label, entry, options = {}) {
    if (!entry) return "";

    const alert = Boolean(options.alert);
    const style = alert
      ? ` style="--pv-metric-bg:${this._escape(options.color)};--pv-metric-text:${this._escape(options.textColor)}"`
      : "";

    return `
      <button class="metric${alert ? " alert" : ""}" data-entity="${this._escape(entry.entity_id)}"${style}>
        <div class="metric-label">${this._escape(label)}</div>
        <div class="metric-value">${this._escape(this._formatState(entry))}</div>
      </button>
    `;
  }

  _formatClock(iso) {
    if (!iso) return "";
    const value = new Date(iso);
    if (Number.isNaN(value.getTime())) {
      const match = String(iso).match(/T(\d{2}):(\d{2})/);
      return match ? `${match[1]}:${match[2]}` : String(iso);
    }
    try {
      return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
      }).format(value);
    } catch (err) {
      return String(iso);
    }
  }

  _scheduleSection(entry) {
    if (!entry || !this._flag("show_today_schedule")) return "";

    const state = this._state(entry);
    const classes = Array.isArray(state?.attributes?.classes)
      ? state.attributes.classes
      : [];

    const rows = classes.map((meeting) => {
      const now = Date.now();
      const startMs = new Date(meeting.start).getTime();
      const endMs = new Date(meeting.end).getTime();
      const isCurrent =
        this._flag("schedule_highlight_current") &&
        Number.isFinite(startMs) &&
        Number.isFinite(endMs) &&
        startMs <= now &&
        now < endMs;

      const bits = [];
      if (this._flag("schedule_show_period") && meeting.period) {
        bits.push(`Period ${meeting.period}`);
      }
      if (this._flag("schedule_show_times") && (meeting.start || meeting.end)) {
        const start = this._formatClock(meeting.start);
        const end = this._formatClock(meeting.end);
        bits.push([start, end].filter(Boolean).join(" – "));
      }
      if (this._flag("schedule_show_teacher") && meeting.teacher) {
        bits.push(meeting.teacher);
      }
      if (this._flag("schedule_show_room") && meeting.room) {
        bits.push(`Room ${meeting.room}`);
      }
      if (this._flag("schedule_show_delivery") && typeof meeting.is_online === "boolean") {
        bits.push(meeting.is_online ? "Online" : "In person");
      }

      return `
        <div class="schedule-row${isCurrent ? " current" : ""}">
          <div class="schedule-name">${this._escape(meeting.name || "Class")}</div>
          ${bits.length ? `<div class="schedule-meta">${this._escape(bits.join(" · "))}</div>` : ""}
        </div>
      `;
    }).join("");

    return `
      <section class="data-section">
        <div class="section-heading">
          <span>Today's schedule</span>
          <button class="section-more" data-entity="${this._escape(entry.entity_id)}">Details</button>
        </div>
        <div class="schedule">
          ${rows || `<div class="empty compact">No classes are listed for today.</div>`}
        </div>
      </section>
    `;
  }

  _courseGroups(entries) {
    const courses = new Map();

    for (const entry of entries) {
      const classified = this._classify(entry);
      if (classified.kind !== "course") continue;
      if (!courses.has(classified.courseKey)) {
        courses.set(classified.courseKey, {});
      }
      courses.get(classified.courseKey)[classified.field] = entry;
    }

    return [...courses.values()].sort((a, b) => {
      const aName = this._courseName(a);
      const bName = this._courseName(b);
      return aName.localeCompare(bName);
    });
  }

  _courseName(fields) {
    const explicit = this._usableState(fields.name);
    if (explicit) return explicit;

    for (const entry of Object.values(fields)) {
      const name = this._state(entry)?.attributes?.course_name;
      if (name) return String(name);
    }
    return "Course";
  }

  _courseRow(fields) {
    const name = this._courseName(fields);
    const secondary = [];

    if (this._flag("show_marking_period")) {
      const value = this._usableState(fields.marking_period);
      if (value) secondary.push(value);
    }
    if (this._flag("show_course_period")) {
      const value = this._usableState(fields.period);
      if (value) secondary.push(`Period ${value}`);
    }
    if (this._flag("show_course_teacher")) {
      const value = this._usableState(fields.teacher);
      if (value) secondary.push(value);
    }
    if (this._flag("show_course_room")) {
      const value = this._usableState(fields.room);
      if (value) secondary.push(`Room ${value}`);
    }
    if (this._flag("show_course_missing")) {
      const value = this._numberState(fields.missing_assignments);
      if (value != null) secondary.push(`${value} missing`);
    }
    if (this._flag("show_course_delivery")) {
      const value = this._usableState(fields.delivery);
      if (value) secondary.push(value);
    }

    const grades = [];
    if (this._flag("show_letter_grade")) {
      const letter = this._usableState(fields.grade);
      if (letter) grades.push(letter);
    }
    if (this._flag("show_grade_percentage")) {
      const percentage = this._usableState(fields.percentage);
      if (percentage) grades.push(`${percentage}%`);
    }

    const target =
      fields.grade ||
      fields.percentage ||
      fields.name ||
      Object.values(fields)[0];

    return `
      <button class="course" ${target ? `data-entity="${this._escape(target.entity_id)}"` : ""}>
        <div class="course-copy">
          <div class="course-name">${this._escape(name)}</div>
          ${secondary.length ? `<div class="course-secondary">${this._escape(secondary.join(" · "))}</div>` : ""}
        </div>
        <div class="course-grade">${this._escape(grades.join(" · ") || "—")}</div>
      </button>
    `;
  }

  _studentData(entries) {
    const byType = {};
    const currentFields = {};
    const nextFields = {};

    for (const entry of entries) {
      const type = this._classify(entry);
      if (type.kind === "course") continue;
      if (type.kind === "current_field") {
        currentFields[type.field] = entry;
        continue;
      }
      if (type.kind === "next_field") {
        nextFields[type.field] = entry;
        continue;
      }
      if (!byType[type.kind]) byType[type.kind] = entry;
    }

    if (!byType.synergy_mail) {
      byType.synergy_mail = this._globalEntry("synergy_mail");
    }

    return { byType, currentFields, nextFields };
  }

  _attendanceTodayMetric(entry) {
    if (!entry) return "";
    const state = this._state(entry);
    const count = this._numberState(entry);
    const attrs = state?.attributes || {};
    const summary = [];

    if (Number(attrs.absences || 0) > 0) summary.push(`${attrs.absences} absent`);
    if (Number(attrs.tardies || 0) > 0) summary.push(`${attrs.tardies} tardy`);
    if (Number(attrs.dismissals || 0) > 0) summary.push(`${attrs.dismissals} dismissal`);

    const label =
      count == null
        ? this._formatState(entry)
        : count === 0
          ? "No attendance events"
          : `${count} attendance ${count === 1 ? "event" : "events"}`;

    return `
      <button class="metric" data-entity="${this._escape(entry.entity_id)}">
        <div class="metric-label">Today's attendance</div>
        <div class="metric-value">${this._escape(label)}</div>
        ${summary.length ? `<div class="metric-meta">${this._escape(summary.join(" · "))}</div>` : ""}
      </button>
    `;
  }

  _attendanceYearMetric(entry) {
    if (!entry) return "";
    const state = this._state(entry);
    const attrs = state?.attributes || {};
    const absences = this._numberState(entry);
    const summary = [];

    if (attrs.tardies != null) summary.push(`${attrs.tardies} tardies`);
    if (attrs.excused_absences != null) summary.push(`${attrs.excused_absences} excused`);
    if (attrs.unexcused_absences != null) summary.push(`${attrs.unexcused_absences} unexcused`);

    const label =
      absences == null
        ? this._formatState(entry)
        : `${absences} ${absences === 1 ? "absence" : "absences"}`;

    return `
      <button class="metric" data-entity="${this._escape(entry.entity_id)}">
        <div class="metric-label">Attendance — school year</div>
        <div class="metric-value">${this._escape(label)}</div>
        ${summary.length ? `<div class="metric-meta">${this._escape(summary.join(" · "))}</div>` : ""}
      </button>
    `;
  }

  _classMetric(label, mainEntry, fields) {
    if (!mainEntry) return "";
    const state = this._state(mainEntry);
    const attrs = state?.attributes || {};
    const meta = [];

    const period = this._usableState(fields.period) || attrs.period;
    const teacher = this._usableState(fields.teacher) || attrs.teacher;
    const room = this._usableState(fields.room) || attrs.room;
    const start = this._usableState(fields.start) || this._formatClock(attrs.start);
    const end = this._usableState(fields.end) || this._formatClock(attrs.end);
    const delivery =
      this._usableState(fields.delivery) ||
      (attrs.is_online === true ? "Online" : attrs.is_online === false ? "In person" : "");

    if (this._flag("schedule_show_period") && period) meta.push(`Period ${period}`);
    if (this._flag("schedule_show_times") && (start || end)) {
      meta.push([start, end].filter(Boolean).join(" – "));
    }
    if (this._flag("schedule_show_teacher") && teacher) meta.push(teacher);
    if (this._flag("schedule_show_room") && room) meta.push(`Room ${room}`);
    if (this._flag("schedule_show_delivery") && delivery) meta.push(delivery);

    return `
      <button class="metric class-metric" data-entity="${this._escape(mainEntry.entity_id)}">
        <div class="metric-label">${this._escape(label)}</div>
        <div class="metric-value">${this._escape(this._formatState(mainEntry))}</div>
        ${meta.length ? `<div class="metric-meta">${this._escape(meta.join(" · "))}</div>` : ""}
      </button>
    `;
  }

  _studentCard(deviceId, entries, options = {}) {
    const { byType, currentFields, nextFields } = this._studentData(entries);
    const courses = this._courseGroups(entries);

    const studentName =
      this._usableState(byType.student_name) || this._deviceName(deviceId, entries);
    const subtitle = [];
    if (this._flag("show_grade_level") && byType.grade_level) {
      const grade = this._usableState(byType.grade_level);
      if (grade) subtitle.push(grade);
    }
    if (this._flag("show_school") && byType.school) {
      const school = this._usableState(byType.school);
      if (school) subtitle.push(school);
    }

    const metrics = [];

    if (this._flag("show_missing_assignments") && byType.missing) {
      const count = this._numberState(byType.missing);
      const rawThreshold = Number(this._value("missing_assignment_threshold"));
      const threshold =
        Number.isFinite(rawThreshold) && rawThreshold >= 0
          ? Math.floor(rawThreshold)
          : DEFAULTS.missing_assignment_threshold;
      const alert = count != null && count > threshold;
      const color = this._alertColor();
      metrics.push(
        this._metric("Missing assignments", byType.missing, {
          alert,
          color,
          textColor: this._contrastText(color),
        })
      );
    }

    if (this._flag("show_current_class")) {
      const html = this._classMetric("Current class", byType.current_class, currentFields);
      if (html) metrics.push(html);
    }
    if (this._flag("show_next_class")) {
      const html = this._classMetric("Next class", byType.next_class, nextFields);
      if (html) metrics.push(html);
    }
    if (this._flag("show_attendance_today") && byType.attendance_today) {
      metrics.push(this._attendanceTodayMetric(byType.attendance_today));
    }
    if (this._flag("show_attendance_year") && byType.attendance_year) {
      metrics.push(this._attendanceYearMetric(byType.attendance_year));
    }
    if (this._flag("show_synergy_mail") && byType.synergy_mail) {
      metrics.push(this._metric("Synergy Mail unread (account)", byType.synergy_mail));
    }

    const courseSection =
      this._flag("show_courses")
        ? `
          <section class="data-section">
            <div class="section-heading"><span>Course grades</span></div>
            <div class="courses">
              ${
                courses.length
                  ? courses.map((fields) => this._courseRow(fields)).join("")
                  : `<div class="empty compact">No course entities are available yet.</div>`
              }
            </div>
          </section>
        `
        : "";

    return `
      <section class="student">
        ${
          options.showStudentHeader
            ? `
              <header class="student-header">
                <div>
                  <h2>${this._escape(studentName)}</h2>
                  ${
                    subtitle.length
                      ? `<div class="subtitle">${this._escape(subtitle.join(" · "))}</div>`
                      : ""
                  }
                </div>
              </header>
            `
            : subtitle.length
              ? `<div class="single-subtitle">${this._escape(subtitle.join(" · "))}</div>`
              : ""
        }

        ${metrics.length ? `<div class="metrics">${metrics.join("")}</div>` : ""}
        ${this._scheduleSection(byType.today_schedule)}
        ${courseSection}
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

  _styles() {
    return `
      <style>
        :host {
          display: block;
          --pv-gap: 14px;
        }
        ha-card {
          display: block;
          background: var(--ha-card-background, var(--card-background-color));
          color: var(--primary-text-color);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow);
          border: var(--ha-card-border-width, 0) solid var(--ha-card-border-color, transparent);
        }
        .card {
          padding: 16px;
        }
        .title {
          font-size: 22px;
          font-weight: 600;
          margin: 0 0 5px;
          overflow-wrap: anywhere;
        }
        .single-subtitle {
          margin-bottom: 14px;
          color: var(--secondary-text-color);
          font-size: 14px;
        }
        .student + .student {
          border-top: 1px solid var(--divider-color);
          padding-top: 18px;
          margin-top: 18px;
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
          grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
          gap: 10px;
          margin: 14px 0 18px;
        }
        button {
          font: inherit;
          color: inherit;
        }
        .metric, .course, .section-more {
          border: 0;
          text-align: left;
          cursor: pointer;
        }
        .metric, .course {
          background: var(--secondary-background-color);
          border-radius: 10px;
        }
        .metric {
          min-height: 82px;
          padding: 12px;
        }
        .metric.alert {
          background: var(--pv-metric-bg);
          color: var(--pv-metric-text);
        }
        .metric.alert .metric-label,
        .metric.alert .metric-meta {
          color: inherit;
          opacity: .86;
        }
        @media (hover: hover) and (pointer: fine) {
          .metric:not(.alert):hover, .course:hover {
            background: color-mix(in srgb, var(--secondary-background-color) 88%, var(--primary-color));
          }
          .section-more:hover {
            text-decoration: underline;
          }
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
        .metric-meta {
          color: var(--secondary-text-color);
          font-size: 11px;
          margin-top: 5px;
          overflow-wrap: anywhere;
        }
        .data-section {
          margin-top: 18px;
        }
        .section-heading {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          margin: 4px 0 8px;
          font-size: 14px;
          font-weight: 600;
          color: var(--secondary-text-color);
        }
        .section-more {
          background: transparent;
          color: var(--primary-color);
          padding: 4px;
          font-size: 12px;
        }
        .schedule, .courses {
          display: grid;
          gap: 8px;
        }
        .schedule-row {
          padding: 10px 12px;
          border-left: 3px solid transparent;
          border-radius: 8px;
          background: var(--secondary-background-color);
        }
        .schedule-row.current {
          border-left-color: var(--primary-color);
          background: color-mix(in srgb, var(--secondary-background-color) 88%, var(--primary-color));
        }
        .schedule-name {
          font-weight: 600;
        }
        .schedule-meta {
          color: var(--secondary-text-color);
          font-size: 12px;
          margin-top: 3px;
          overflow-wrap: anywhere;
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
          text-align: right;
          font-size: 17px;
          font-weight: 700;
        }
        .empty, .loading {
          color: var(--secondary-text-color);
          padding: 12px 0;
        }
        .empty.compact {
          padding: 8px 0;
        }
        @media (max-width: 450px) {
          .metrics {
            grid-template-columns: 1fr;
          }
          .course {
            align-items: flex-start;
          }
          .course-grade {
            max-width: 40%;
          }
        }
      </style>
    `;
  }

  _render() {
    if (!this.shadowRoot) return;

    const styles = this._styles();

    if (!this._hass) {
      this.shadowRoot.innerHTML = `${styles}<ha-card><div class="card loading">Waiting for Home Assistant…</div></ha-card>`;
      return;
    }

    if (!this._registryLoaded) {
      this.shadowRoot.innerHTML = `${styles}<ha-card><div class="card loading">Loading ParentVUE dashboard…</div></ha-card>`;
      return;
    }

    const selected = this._selectedGroups();
    const requestedDevice = String(this._config.child_device_id || "");

    if (requestedDevice && selected.length === 0) {
      this.shadowRoot.innerHTML = `
        ${styles}
        <ha-card>
          <div class="card">
            <div class="empty">The selected ParentVUE child is no longer available. Edit the card and select another child.</div>
          </div>
        </ha-card>
      `;
      return;
    }

    if (selected.length === 0) {
      this.shadowRoot.innerHTML = `
        ${styles}
        <ha-card>
          <div class="card">
            <div class="empty">No ParentVUE entities were found. Confirm the ParentVUE integration is configured and loaded.</div>
          </div>
        </ha-card>
      `;
      return;
    }

    const singleChild = selected.length === 1 && Boolean(requestedDevice);
    let defaultTitle = "ParentVUE";
    if (singleChild) {
      defaultTitle = this._deviceName(selected[0][0], selected[0][1]);
    }

    let title = defaultTitle;
    if (Object.prototype.hasOwnProperty.call(this._config, "title")) {
      if (this._config.title === false) {
        title = "";
      } else if (String(this._config.title || "").trim()) {
        title = String(this._config.title).trim();
      }
    }

    const content = selected
      .map(([deviceId, entries]) =>
        this._studentCard(deviceId, entries, {
          showStudentHeader: !singleChild,
        })
      )
      .join("");

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

class ParentVueDashboardCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = { ...DEFAULTS };
    this._entries = [];
    this._devices = new Map();
    this._loadingRegistry = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._loadingRegistry && this._entries.length === 0) {
      this._loadRegistry();
    } else {
      this._render();
    }
  }

  setConfig(config) {
    this._config = { ...DEFAULTS, ...(config || {}) };
    this._render();
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
        (entry) => entry.platform === INTEGRATION_DOMAIN
      );
      this._devices = new Map(
        (devices || []).map((device) => [device.id, device])
      );
    } catch (err) {
      console.warn("ParentVUE card editor could not load Home Assistant registries.");
    } finally {
      this._loadingRegistry = false;
      this._render();
    }
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _deviceOptions() {
    const ids = [...new Set(this._entries.map((entry) => entry.device_id).filter(Boolean))];
    return ids
      .map((id) => {
        const device = this._devices.get(id);
        return {
          id,
          name: device?.name_by_user || device?.name || "ParentVUE student",
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  _emit(next) {
    this._config = next;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: next },
        bubbles: true,
        composed: true,
      })
    );
  }

  _onInput(event) {
    const target = event.target;
    const key = target?.dataset?.key;
    if (!key) return;

    const next = { ...this._config };

    if (target.type === "checkbox") {
      next[key] = Boolean(target.checked);
    } else if (key === "missing_assignment_threshold") {
      const value = Number(target.value);
      next[key] = Number.isFinite(value) && value >= 0 ? Math.floor(value) : 0;
    } else if (key === "child_device_id") {
      if (target.value) next[key] = target.value;
      else delete next[key];
    } else if (key === "title") {
      const value = String(target.value || "").trim();
      if (value) next[key] = value;
      else delete next[key];
    } else {
      next[key] = target.value;
    }

    this._emit(next);
  }

  _toggleRows(group) {
    return BOOLEAN_FIELDS
      .filter(([section]) => section === group)
      .map(([, key, label]) => `
        <label class="toggle-row">
          <span>${this._escape(label)}</span>
          <input type="checkbox" data-key="${this._escape(key)}" ${this._config[key] !== false ? "checked" : ""}>
        </label>
      `)
      .join("");
  }

  _render() {
    if (!this.shadowRoot) return;

    const devices = this._deviceOptions();
    const selected = String(this._config.child_device_id || "");

    const group = (title, body, open = false) => `
      <details ${open ? "open" : ""}>
        <summary>${this._escape(title)}</summary>
        <div class="group">${body}</div>
      </details>
    `;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          color: var(--primary-text-color);
        }
        .editor {
          display: grid;
          gap: 12px;
          padding: 4px 0 12px;
        }
        label.field {
          display: grid;
          gap: 6px;
          font-size: 13px;
          color: var(--secondary-text-color);
        }
        input[type="text"], input[type="number"], select {
          box-sizing: border-box;
          width: 100%;
          min-height: 44px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          padding: 9px 10px;
          font: inherit;
          font-size: 16px;
        }
        input[type="color"] {
          width: 52px;
          min-height: 42px;
          border: 0;
          background: transparent;
          padding: 0;
        }
        details {
          border-top: 1px solid var(--divider-color);
          padding-top: 8px;
        }
        summary {
          cursor: pointer;
          font-weight: 600;
          padding: 7px 0;
        }
        .group {
          display: grid;
          gap: 2px;
          padding: 4px 0 8px;
        }
        .toggle-row {
          min-height: 44px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .toggle-row input {
          width: 22px;
          height: 22px;
        }
        .inline {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 12px;
          align-items: end;
        }
        .hint {
          color: var(--secondary-text-color);
          font-size: 12px;
          line-height: 1.4;
          margin-top: 4px;
        }
      </style>

      <div class="editor">
        <label class="field">
          Child
          <select data-key="child_device_id">
            <option value="" ${!selected ? "selected" : ""}>All children</option>
            ${devices.map((device) => `
              <option value="${this._escape(device.id)}" ${device.id === selected ? "selected" : ""}>
                ${this._escape(device.name)}
              </option>
            `).join("")}
          </select>
        </label>

        <label class="field">
          Custom title (optional)
          <input
            type="text"
            data-key="title"
            value="${this._escape(typeof this._config.title === "string" ? this._config.title : "")}"
            placeholder="Uses the selected student's name"
          >
        </label>

        ${group("Student", this._toggleRows("Student"), true)}
        ${group(
          "Assignments",
          `
            ${this._toggleRows("Assignments")}
            <div class="inline">
              <label class="field">
                Alert when missing assignments are greater than
                <input
                  type="number"
                  min="0"
                  step="1"
                  data-key="missing_assignment_threshold"
                  value="${this._escape(this._config.missing_assignment_threshold ?? DEFAULTS.missing_assignment_threshold)}"
                >
              </label>
              <label class="field">
                Alert color
                <input
                  type="color"
                  data-key="missing_assignment_alert_color"
                  value="${this._escape(this._config.missing_assignment_alert_color || DEFAULTS.missing_assignment_alert_color)}"
                >
              </label>
            </div>
          `,
          true
        )}
        ${group("Schedule", this._toggleRows("Schedule"), true)}
        ${group("Schedule details", this._toggleRows("Schedule details"))}
        ${group("Courses", this._toggleRows("Courses"), true)}
        ${group("Course details", this._toggleRows("Course details"))}
        ${group(
          "Attendance & Synergy Mail",
          `
            ${this._toggleRows("Attendance & mail")}
            <div class="hint">
              These sections appear only when the corresponding ParentVUE entities are available.
            </div>
          `
        )}
      </div>
    `;

    this.shadowRoot.querySelectorAll("input, select").forEach((element) => {
      const eventName =
        element.type === "text" || element.type === "number"
          ? "change"
          : "change";
      element.addEventListener(eventName, (event) => this._onInput(event));
    });
  }
}

if (!customElements.get(CARD_NAME)) {
  customElements.define(CARD_NAME, ParentVueDashboardCard);
}
if (!customElements.get(EDITOR_NAME)) {
  customElements.define(EDITOR_NAME, ParentVueDashboardCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_NAME)) {
  window.customCards.push({
    type: CARD_NAME,
    name: "ParentVUE Dashboard",
    description: "Configurable per-student ParentVUE dashboard card.",
    preview: true,
  });
}
