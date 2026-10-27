import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TextInput from "../TextInput";

describe("<TextInput />", () => {
  it("renders a textarea with the provided value", () => {
    render(<TextInput text="hello" setText={() => {}} onSubmit={() => {}} />);
    const textarea = screen.getByPlaceholderText(/Paste full contract text here/i);
    expect(textarea).toHaveValue("hello");
  });

  it("calls setText on every keystroke", async () => {
    const setText = vi.fn();
    render(<TextInput text="" setText={setText} onSubmit={() => {}} />);
    const user = userEvent.setup();
    await user.type(screen.getByRole("textbox"), "ab");
    // user.type invokes onChange per keystroke
    expect(setText).toHaveBeenCalledTimes(2);
    expect(setText).toHaveBeenLastCalledWith("b");
  });

  it("disables the submit button when text is blank", () => {
    render(<TextInput text="   " setText={() => {}} onSubmit={() => {}} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("disables the submit button when loading is true", () => {
    render(<TextInput text="abc" setText={() => {}} onSubmit={() => {}} loading />);
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent(/Processing/i);
  });

  it("triggers onSubmit when clicked with valid text", async () => {
    const onSubmit = vi.fn();
    render(<TextInput text="abc" setText={() => {}} onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("disables the textarea while loading", () => {
    render(<TextInput text="abc" setText={() => {}} onSubmit={() => {}} loading />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });
});
