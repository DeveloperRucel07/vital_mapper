import { describe, expect, it } from "vitest";
import { ApiError, errorForStatus } from "./errors";

describe("API error mapping", () => {
  it("maps authentication failures without exposing backend details", () => {
    const error = errorForStatus(401);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.kind).toBe("authentication");
    expect(error.message).not.toContain("JWT");
  });

  it("maps validation and server errors consistently", () => {
    expect(errorForStatus(422).kind).toBe("validation");
    expect(errorForStatus(503).kind).toBe("server");
  });
});
