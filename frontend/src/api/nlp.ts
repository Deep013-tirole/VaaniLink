import { apiClient } from "./client";
import { NLPAnalyzeResult } from "@/types";

export interface TransliteratePayload {
  text: string;
  source_lang?: string;
  target_script?: string;
}

export interface TransliterateResult {
  original_text: string;
  source_lang: string;
  target_script: string;
  transliterated_text: string;
}

export async function analyzeText(text: string): Promise<NLPAnalyzeResult> {
  return apiClient<NLPAnalyzeResult>("/api/v1/nlp/analyze/", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function transliterateText(
  payload: TransliteratePayload
): Promise<TransliterateResult> {
  return apiClient<TransliterateResult>("/api/v1/nlp/transliterate/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
