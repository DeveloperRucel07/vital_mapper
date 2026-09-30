const DATABASE_NAME = "vital-mapper-offline-recordings";
const DATABASE_VERSION = 1;
const KEY_STORE = "keys";
const RECORDING_STORE = "recordings";
const AUDIO_KEY_ID = "audio-v1";
const ADDITIONAL_DATA = new TextEncoder().encode("vital-mapper-offline-recording:v1");
let activeEncryptionKey: Promise<CryptoKey> | null = null;

type StoredRecording = {
  id: string;
  iv: ArrayBuffer;
  ciphertext: ArrayBuffer;
};

type RecordingMetadata = {
  ownerId: string;
  patientRef: string;
  recordingId: string;
  startedAt: string;
  contentType: string;
};

export type OfflineRecording = RecordingMetadata & {
  audio: Blob;
};

export type OfflineSyncResult = {
  synchronized: number;
  remaining: number;
};

function unavailable(): Error {
  return new Error("Dieser Browser unterstützt keinen verschlüsselten Offline-Speicher.");
}

function supportsSecureOfflineStorage(): boolean {
  return typeof indexedDB !== "undefined" && typeof crypto !== "undefined" && !!crypto.subtle;
}

function openDatabase(): Promise<IDBDatabase> {
  if (!supportsSecureOfflineStorage()) return Promise.reject(unavailable());

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(KEY_STORE)) database.createObjectStore(KEY_STORE);
      if (!database.objectStoreNames.contains(RECORDING_STORE)) {
        database.createObjectStore(RECORDING_STORE, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Offline-Speicher konnte nicht geöffnet werden."));
  });
}

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Offline-Speicher konnte nicht gelesen werden."));
  });
}

async function readKey(): Promise<CryptoKey | undefined> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(KEY_STORE, "readonly");
    return await requestResult(transaction.objectStore(KEY_STORE).get(AUDIO_KEY_ID));
  } finally {
    database.close();
  }
}

async function saveKey(key: CryptoKey): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(KEY_STORE, "readwrite");
    await requestResult(transaction.objectStore(KEY_STORE).put(key, AUDIO_KEY_ID));
  } finally {
    database.close();
  }
}

async function encryptionKey(): Promise<CryptoKey> {
  if (!activeEncryptionKey) {
    activeEncryptionKey = (async () => {
      const existing = await readKey();
      if (existing) return existing;

      const generated = await crypto.subtle.generateKey(
        { name: "AES-GCM", length: 256 },
        false,
        ["encrypt", "decrypt"],
      );
      await saveKey(generated);
      return generated;
    })();
  }
  try {
    return await activeEncryptionKey;
  } catch (error) {
    activeEncryptionKey = null;
    throw error;
  }
}

async function encode(recording: OfflineRecording): Promise<ArrayBuffer> {
  const metadata: RecordingMetadata = {
    ownerId: recording.ownerId,
    patientRef: recording.patientRef,
    recordingId: recording.recordingId,
    startedAt: recording.startedAt,
    contentType: recording.contentType,
  };
  const metadataBytes = new TextEncoder().encode(JSON.stringify(metadata));
  const audioBytes = await recording.audio.arrayBuffer();
  const payload = new Uint8Array(4 + metadataBytes.byteLength + audioBytes.byteLength);
  new DataView(payload.buffer).setUint32(0, metadataBytes.byteLength);
  payload.set(metadataBytes, 4);
  payload.set(new Uint8Array(audioBytes), 4 + metadataBytes.byteLength);
  return payload.buffer;
}

function decode(payload: ArrayBuffer): OfflineRecording {
  const bytes = new Uint8Array(payload);
  if (bytes.byteLength < 4) throw new Error("Ungültige lokale Aufnahme.");
  const metadataLength = new DataView(payload).getUint32(0);
  const audioOffset = 4 + metadataLength;
  if (audioOffset > bytes.byteLength) throw new Error("Ungültige lokale Aufnahme.");

  const metadata = JSON.parse(
    new TextDecoder().decode(bytes.slice(4, audioOffset)),
  ) as RecordingMetadata;
  if (
    !metadata.ownerId ||
    !metadata.patientRef ||
    !metadata.recordingId ||
    !metadata.startedAt ||
    !metadata.contentType
  ) {
    throw new Error("Ungültige lokale Aufnahme.");
  }
  return {
    ...metadata,
    audio: new Blob([bytes.slice(audioOffset)], { type: metadata.contentType }),
  };
}

export async function encryptOfflinePayload(
  recording: OfflineRecording,
  key: CryptoKey,
): Promise<Pick<StoredRecording, "iv" | "ciphertext">> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv, additionalData: ADDITIONAL_DATA },
    key,
    await encode(recording),
  );
  return { iv: iv.buffer, ciphertext };
}

export async function decryptOfflinePayload(
  stored: Pick<StoredRecording, "iv" | "ciphertext">,
  key: CryptoKey,
): Promise<OfflineRecording> {
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: new Uint8Array(stored.iv), additionalData: ADDITIONAL_DATA },
    key,
    stored.ciphertext,
  );
  return decode(plaintext);
}

export async function encryptOfflineRecording(recording: OfflineRecording): Promise<StoredRecording> {
  return { id: crypto.randomUUID(), ...(await encryptOfflinePayload(recording, await encryptionKey())) };
}

export async function decryptOfflineRecording(stored: StoredRecording): Promise<OfflineRecording> {
  return decryptOfflinePayload(stored, await encryptionKey());
}

async function listStoredRecordings(): Promise<StoredRecording[]> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(RECORDING_STORE, "readonly");
    return await requestResult(transaction.objectStore(RECORDING_STORE).getAll());
  } finally {
    database.close();
  }
}

async function saveStoredRecording(recording: StoredRecording): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(RECORDING_STORE, "readwrite");
    await requestResult(transaction.objectStore(RECORDING_STORE).put(recording));
  } finally {
    database.close();
  }
}

async function deleteStoredRecording(id: string): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(RECORDING_STORE, "readwrite");
    await requestResult(transaction.objectStore(RECORDING_STORE).delete(id));
  } finally {
    database.close();
  }
}

async function recordsForOwner(ownerId: string): Promise<StoredRecording[]> {
  const records = await listStoredRecordings();
  const owned: StoredRecording[] = [];
  for (const record of records) {
    try {
      if ((await decryptOfflineRecording(record)).ownerId === ownerId) owned.push(record);
    } catch {
      // Ohne Schlüssel oder bei manipuliertem Chiffrat ist keine Wiederherstellung möglich.
      await deleteStoredRecording(record.id);
    }
  }
  return owned;
}

export async function queueOfflineRecording(recording: OfflineRecording): Promise<void> {
  await saveStoredRecording(await encryptOfflineRecording(recording));
}

export async function offlineRecordingCount(ownerId: string): Promise<number> {
  return (await recordsForOwner(ownerId)).length;
}

export async function discardOfflineRecordings(ownerId: string): Promise<void> {
  for (const record of await recordsForOwner(ownerId)) await deleteStoredRecording(record.id);
}

export async function synchronizeOfflineRecordings(
  ownerId: string,
  upload: (recording: OfflineRecording) => Promise<void>,
): Promise<OfflineSyncResult> {
  const records = await recordsForOwner(ownerId);
  let synchronized = 0;

  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    try {
      const recording = await decryptOfflineRecording(record);
      await upload(recording);
      await deleteStoredRecording(record.id);
      synchronized += 1;
    } catch {
      return { synchronized, remaining: records.length - synchronized };
    }
  }
  return { synchronized, remaining: 0 };
}
