export interface CustomVoice {
  /** Unique display name — keyPath in IndexedDB, shown in preset lists */
  name: string;
  /** Where the voice comes from */
  origin: "clone" | "design";
  /** Qwen language for synthesis (e.g. "Spanish", "English", "Auto") */
  language: string;
  /** Persona description (design origin) — backend builds/caches the ref */
  design_prompt: string;
  /** Transcript of the reference clip (clone origin, may be empty) */
  ref_text: string;
  /** Backend path of the reference clip, e.g. static/assets/qwen_refs/x.mp3 */
  refAudioPath: string;
  createdAt: number;
  updatedAt?: number;
}

export interface QwenVoiceParams {
  qwen_mode: string;
  qwen_lang: string;
  qwen_instruct: string;
  qwen_design_prompt: string;
  qwen_clone_ref: string;
  qwen_clone_text: string;
}

const isValidName = (name: string) =>
  !!name && name.trim().length > 0 && name.trim().length <= 40 &&
  !/[/\\:*?"<>|]/.test(name);

export const useCustomVoices = () => {
  const { saveCustomVoice, getCustomVoice, getAllCustomVoices, deleteCustomVoice } =
    useIndexedDB();

  const list = async (): Promise<CustomVoice[]> => {
    try {
      const all = await getAllCustomVoices();
      return (all || []).sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    } catch (e) {
      console.error("Failed to load custom voices:", e);
      return [];
    }
  };

  const get = async (name: string): Promise<CustomVoice | null> => {
    if (!name) return null;
    try {
      return await getCustomVoice(name);
    } catch (e) {
      console.error("Failed to load custom voice:", e);
      return null;
    }
  };

  /** Create or update (same name overwrites) a custom voice. */
  const save = async (voice: Omit<CustomVoice, "createdAt" | "updatedAt">): Promise<{ ok: boolean; updated: boolean; error?: string }> => {
    const name = (voice.name || "").trim();
    if (!isValidName(name)) {
      return { ok: false, updated: false, error: "Name needs 1-40 chars, no / \\ : * ? \" < > |" };
    }
    if (voice.origin === "clone" && !voice.refAudioPath) {
      return { ok: false, updated: false, error: "Upload a reference clip first" };
    }
    if (voice.origin === "design" && !voice.design_prompt.trim()) {
      return { ok: false, updated: false, error: "Write a voice description first" };
    }
    try {
      const existing = await getCustomVoice(name);
      const entry: CustomVoice = {
        ...voice,
        name,
        createdAt: existing?.createdAt || Date.now(),
      };
      await saveCustomVoice(entry);
      return { ok: true, updated: !!existing };
    } catch (e: any) {
      console.error("Failed to save custom voice:", e);
      return { ok: false, updated: false, error: e?.message || "IndexedDB save failed" };
    }
  };

  const remove = async (name: string): Promise<boolean> => {
    try {
      await deleteCustomVoice(name);
      return true;
    } catch (e) {
      console.error("Failed to delete custom voice:", e);
      return false;
    }
  };

  /**
   * Explicit synthesis params for a saved voice — sent with preview and
   * generation requests so the backend needs no prior global state
   * (survives backend restarts).
   */
  const toQwenParams = (voice: CustomVoice): QwenVoiceParams => ({
    qwen_mode: voice.origin === "design" ? "design" : "clone",
    qwen_lang: voice.language || "Auto",
    qwen_instruct: "",
    qwen_design_prompt: voice.origin === "design" ? voice.design_prompt : "",
    qwen_clone_ref: voice.origin === "clone" ? voice.refAudioPath : "",
    qwen_clone_text: voice.origin === "clone" ? voice.ref_text : "",
  });

  return { list, get, save, remove, toQwenParams, isValidName };
};
