/**
 * Typed fetch wrapper (T022).
 *
 * Every API call goes through here so:
 *   1. problem+JSON 4xx/5xx responses become typed `ApiError` instances
 *      carrying the backend's stable error code + i18n message_key (R6).
 *   2. Successful responses are runtime-validated against the Zod schema in
 *      `schemas.ts`. A schema mismatch is a bug, not a user-facing error.
 */
import { ZodSchema } from "zod";

import { problemDetailSchema } from "@/api/schemas";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly messageKey: string;

  constructor({
    status,
    code,
    messageKey,
  }: {
    status: number;
    code: string;
    messageKey: string;
  }) {
    super(`${code} [${status}] ${messageKey}`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.messageKey = messageKey;
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

interface RequestOptions<TResponse> {
  method?: "GET" | "POST";
  path: string;
  body?: unknown;
  responseSchema: ZodSchema<TResponse>;
  signal?: AbortSignal;
}

interface VoidRequestOptions {
  method: "POST";
  path: string;
  body?: unknown;
  responseSchema?: undefined;
  signal?: AbortSignal;
}

async function readProblem(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return new ApiError({
      status: response.status,
      code: "unknown_error",
      messageKey: "errors.generic",
    });
  }
  const parsed = problemDetailSchema.safeParse(body);
  if (!parsed.success) {
    return new ApiError({
      status: response.status,
      code: "unknown_error",
      messageKey: "errors.generic",
    });
  }
  return new ApiError({
    status: response.status,
    code: parsed.data.error,
    messageKey: parsed.data.message_key,
  });
}

export async function apiRequest<TResponse>(
  options: RequestOptions<TResponse>,
): Promise<TResponse>;
export async function apiRequest(options: VoidRequestOptions): Promise<void>;
export async function apiRequest<TResponse>(
  options: RequestOptions<TResponse> | VoidRequestOptions,
): Promise<TResponse | void> {
  const { method = "GET", path, body, signal } = options;
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") throw err;
    throw new NetworkError(err instanceof Error ? err.message : "network_error");
  }

  if (!response.ok) {
    throw await readProblem(response);
  }

  if (options.responseSchema === undefined) {
    return;
  }

  const json = await response.json();
  const parsed = options.responseSchema.safeParse(json);
  if (!parsed.success) {
    // Schema mismatch is an engineering bug, not a user-facing condition.
    // Surface it loudly in dev; map to a generic error in prod.
    if (import.meta.env.DEV) {
      console.error("API schema mismatch", parsed.error.flatten());
    }
    throw new ApiError({
      status: 500,
      code: "schema_mismatch",
      messageKey: "errors.generic",
    });
  }
  return parsed.data;
}
