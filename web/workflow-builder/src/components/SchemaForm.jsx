// components/SchemaForm.jsx
import React from "react";

function SchemaForm({ schema, values, onChange }) {
  if (!schema || !schema.properties) return null;

  const props = schema.properties || {};

  function handleChange(key, newValue) {
    onChange({ [key]: newValue });
  }

  return (
    <div className="schema-form">
      {Object.entries(props).map(([key, prop]) => (
        <Field
          key={key}
          name={key}
          prop={prop}
          value={values?.[key] ?? prop.default ?? ""}
          onChange={handleChange}
        />
      ))}
    </div>
  );
}

function Field({ name, prop, value, onChange }) {
  const label = prop.title || name;
  const desc = prop.description;

  if (prop.enum) {
    return (
      <div className="schema-field">
        <label>{label}</label>
        {desc && <span className="field-desc">{desc}</span>}
        <select value={value} onChange={(e) => onChange(name, e.target.value)}>
          {prop.enum.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (prop.type === "boolean") {
    return (
      <div className="schema-field schema-field-checkbox">
        <label>
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => onChange(name, e.target.checked)}
          />
          {label}
        </label>
        {desc && <span className="field-desc">{desc}</span>}
      </div>
    );
  }

  if (prop.type === "integer" || prop.type === "number") {
    return (
      <div className="schema-field">
        <label>{label}</label>
        {desc && <span className="field-desc">{desc}</span>}
        <input
          type="number"
          step={prop.type === "number" ? "any" : "1"}
          value={value}
          onChange={(e) =>
            onChange(
              name,
              prop.type === "integer" ? parseInt(e.target.value, 10) : parseFloat(e.target.value)
            )
          }
        />
      </div>
    );
  }

  if (prop.type === "array") {
    return (
      <div className="schema-field">
        <label>{label}</label>
        {desc && <span className="field-desc">{desc}</span>}
        <input
          type="text"
          value={Array.isArray(value) ? value.join(", ") : String(value)}
          onChange={(e) =>
            onChange(
              name,
              e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
            )
          }
          placeholder="Comma-separated values"
        />
      </div>
    );
  }

  // Default: string / text
  return (
    <div className="schema-field">
      <label>{label}</label>
      {desc && <span className="field-desc">{desc}</span>}
      {prop.format === "textarea" ? (
        <textarea
          rows={4}
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
        />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(name, e.target.value)} />
      )}
    </div>
  );
}

export default SchemaForm;
