import { describe, it, expect, beforeEach } from "vitest";
import useAuthStore from "../useAuthStore";

describe("useAuthStore", () => {
  beforeEach(() => {
    // Reset store between tests so state does not leak.
    useAuthStore.setState({ user: null });
  });

  it("starts with user=null", () => {
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("setUser stores the provided user object", () => {
    const user = { id: 1, name: "Alice", email: "alice@example.com", is_admin: false };
    useAuthStore.getState().setUser(user);
    expect(useAuthStore.getState().user).toEqual(user);
  });

  it("logout clears the user", () => {
    useAuthStore.getState().setUser({ id: 1, name: "Bob" });
    expect(useAuthStore.getState().user).not.toBeNull();
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("setUser overwrites a previous user", () => {
    useAuthStore.getState().setUser({ id: 1, name: "Alice" });
    useAuthStore.getState().setUser({ id: 2, name: "Bob" });
    expect(useAuthStore.getState().user).toEqual({ id: 2, name: "Bob" });
  });
});
