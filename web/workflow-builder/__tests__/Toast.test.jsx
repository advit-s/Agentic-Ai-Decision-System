// __tests__/Toast.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ToastProvider, useToast } from "../src/components/Toast";
import React from "react";

function TestConsumer() {
  const { showToast } = useToast();
  return <button onClick={() => showToast("Test message", "info")}>Show Toast</button>;
}

describe("Toast", () => {
  it("renders children", () => {
    render(<ToastProvider><div>Content</div></ToastProvider>);
    expect(screen.getByText("Content")).toBeDefined();
  });

  it("provides showToast via context", () => {
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    expect(screen.getByText("Show Toast")).toBeDefined();
  });
});
