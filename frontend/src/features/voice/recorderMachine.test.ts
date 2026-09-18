import { describe, expect, it } from "vitest";
import { initialRecorderState, recorderReducer } from "./recorderMachine";

describe("recorder state", () => {
  it("supports start, pause, resume and stop", () => {
    let state = recorderReducer(initialRecorderState, { type: "start" });
    expect(state.status).toBe("recording");
    state = recorderReducer(state, { type: "tick" });
    expect(state.durationSeconds).toBe(1);
    state = recorderReducer(state, { type: "pause" });
    expect(state.status).toBe("paused");
    state = recorderReducer(state, { type: "resume" });
    state = recorderReducer(state, { type: "stop" });
    expect(state.status).toBe("stopped");
  });

  it("clears the transient recording state on discard", () => {
    const recording = recorderReducer(initialRecorderState, { type: "start" });
    const discarded = recorderReducer(recording, { type: "discard" });
    expect(discarded).toEqual(initialRecorderState);
  });
});
