import {render, fireEvent, cleanup} from "@testing-library/react";
import {it, expect, vi, afterEach} from "vitest";
import {LlmBuilderModal} from "./LlmBuilderModal";

afterEach(() => {
  cleanup();
});

it("renders AI Graph Architect modal when open", () => {
  const onClose = vi.fn();
  const onApply = vi.fn();
  const {getByText, getByPlaceholderText} = render(
    <LlmBuilderModal isOpen={true} onClose={onClose} onApplyGraph={onApply} />
  );
  expect(getByText(/AI Agent Architect/i)).toBeTruthy();
  expect(getByPlaceholderText(/Baue einen autonomen ReAct-Agenten/i)).toBeTruthy();
});

it("does not render when closed", () => {
  const onClose = vi.fn();
  const onApply = vi.fn();
  const {container} = render(<LlmBuilderModal isOpen={false} onClose={onClose} onApplyGraph={onApply} />);
  expect(container.firstChild).toBeNull();
});

it("populates prompt when clicking a preset chip", () => {
  const onClose = vi.fn();
  const onApply = vi.fn();
  const {container, getAllByText} = render(
    <LlmBuilderModal isOpen={true} onClose={onClose} onApplyGraph={onApply} />
  );
  const presetBtn = getAllByText(/ReAct Loop mit Pytest/i)[0];
  fireEvent.click(presetBtn);
  const textarea = container.querySelector("textarea") as HTMLTextAreaElement;
  expect(textarea.value).toContain("Pytest");
});
