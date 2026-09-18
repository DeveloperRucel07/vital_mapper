export type RecorderStatus = "idle" | "recording" | "paused" | "stopped" | "error";

export interface RecorderState {
  status: RecorderStatus;
  durationSeconds: number;
  error: string | null;
}

export const initialRecorderState: RecorderState = {
  status: "idle",
  durationSeconds: 0,
  error: null,
};

export type RecorderAction =
  | { type: "start" }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "stop" }
  | { type: "tick" }
  | { type: "discard" }
  | { type: "error"; message: string };

export function recorderReducer(state: RecorderState, action: RecorderAction): RecorderState {
  switch (action.type) {
    case "start":
      return { status: "recording", durationSeconds: 0, error: null };
    case "pause":
      return state.status === "recording" ? { ...state, status: "paused" } : state;
    case "resume":
      return state.status === "paused" ? { ...state, status: "recording" } : state;
    case "stop":
      return ["recording", "paused"].includes(state.status) ? { ...state, status: "stopped" } : state;
    case "tick":
      return state.status === "recording" ? { ...state, durationSeconds: state.durationSeconds + 1 } : state;
    case "discard":
      return initialRecorderState;
    case "error":
      return { ...state, status: "error", error: action.message };
  }
}
