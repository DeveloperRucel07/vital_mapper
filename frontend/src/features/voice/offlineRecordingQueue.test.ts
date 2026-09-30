import { describe, expect, it } from "vitest";
import { webcrypto } from "node:crypto";
import {
  decryptOfflinePayload,
  encryptOfflinePayload,
} from "./offlineRecordingQueue";

describe("offline recording encryption", () => {
  it("keeps metadata and audio readable only after AES-GCM decryption", async () => {
    const cryptoBeforeTest = globalThis.crypto;
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });

    try {
      const key = await crypto.subtle.generateKey(
        { name: "AES-GCM", length: 256 },
        false,
        ["encrypt", "decrypt"],
      );
      const stored = await encryptOfflinePayload({
        ownerId: "user-1",
        patientRef: "patient-7",
        recordingId: "018bcfe5-6800-7abc-8def-0123456789ab",
        startedAt: "2026-09-30T10:00:00Z",
        contentType: "audio/webm",
        audio: new Blob(["synthetic audio"], { type: "audio/webm" }),
      }, key);
      expect(new TextDecoder().decode(stored.ciphertext)).not.toContain("patient-7");
      const decrypted = await decryptOfflinePayload(stored, key);
      expect(decrypted.patientRef).toBe("patient-7");
      expect(await decrypted.audio.text()).toBe("synthetic audio");
    } finally {
      Object.defineProperty(globalThis, "crypto", { configurable: true, value: cryptoBeforeTest });
    }
  });
});
