// __tests__/SchemaForm.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SchemaForm from "../src/components/SchemaForm";
import React from "react";

describe("SchemaForm", () => {
  const basicSchema = {
    type: "object",
    properties: {
      name: { type: "string", title: "Name", default: "hello" },
      count: { type: "integer", title: "Count", default: 5 },
      enabled: { type: "boolean", title: "Enabled", default: true },
      severity: {
        type: "string",
        title: "Severity",
        default: "low",
        enum: ["low", "high"],
      },
      tags: { type: "array", title: "Tags", items: { type: "string" } },
    },
  };

  it("renders all field types from schema", () => {
    const values = {};
    render(
      <SchemaForm
        schema={basicSchema}
        values={values}
        onChange={(v) => Object.assign(values, v)}
      />
    );
    expect(screen.getByDisplayValue("hello")).toBeDefined();
    expect(screen.getByDisplayValue("5")).toBeDefined();
    expect(screen.getByText("low")).toBeDefined();
  });

  it("calls onChange when text input changes", () => {
    const onChange = [];
    render(
      <SchemaForm
        schema={basicSchema}
        values={{}}
        onChange={(v) => onChange.push(v)}
      />
    );
    const input = screen.getByDisplayValue("hello");
    fireEvent.change(input, { target: { value: "world" } });
    expect(onChange.length).toBeGreaterThanOrEqual(1);
  });

  it("renders empty form for empty schema", () => {
    const { container } = render(
      <SchemaForm
        schema={{ type: "object", properties: {} }}
        values={{}}
        onChange={() => {}}
      />
    );
    expect(container.textContent).toBe("");
  });
});
