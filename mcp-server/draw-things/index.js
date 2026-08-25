#!/usr/bin/env node
/**
 * Draw Things MCP Server
 *
 * stdio JSON-RPC обёртка к Draw Things HTTP API (SDXL backend).
 *
 * Tool: generate_image — отправляет prompt на Draw Things и возвращает
 * готовый PNG как base64 в MCP ответе (или путь к сохранённому файлу).
 *
 * Env:
 *   DRAW_THINGS_URL — базовый URL Draw Things (default: http://127.0.0.1:7860)
 *   DRAW_THINGS_TIMEOUT — таймаут в секундах (default: 300)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "fs";
import path from "path";
import os from "os";

// ⚠️ КРИТИЧНО для stdio MCP — никакого console.log, только console.error в stderr!
const DEBUG = process.env.DRAW_THINGS_DEBUG === "1";
const log = (...args) => DEBUG && console.error("[draw-things]", ...args);

const API_BASE = process.env.DRAW_THINGS_URL || "http://127.0.0.1:7860";
const TIMEOUT_SEC = parseInt(process.env.DRAW_THINGS_TIMEOUT || "300", 10);

/**
 * Fetch с классическим таймаутом через AbortController.
 * Возвращает Response или throws Error после таймаута.
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = TIMEOUT_SEC * 1000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return res;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch текущих опций Draw Things (модель, sampler, LoRA).
 */
async function fetchOptions() {
  const res = await fetchWithTimeout(`${API_BASE}/sdapi/v1/options`, {}, 10_000);
  if (!res.ok) throw new Error(`Options HTTP ${res.status}`);
  return res.json();
}

/**
 * Универсальный POST к Draw Things.
 * Возвращает JSON-ответ (для txt2img — { images: ["base64,..."] }).
 */
async function postToDrawThings(endpoint, body) {
  const res = await fetchWithTimeout(
    `${API_BASE}${endpoint}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    TIMEOUT_SEC * 1000
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

/**
 * Сохраняет base64 PNG на диск и возвращает путь.
 */
function saveBase64Png(base64Data, prefix = "draw-things") {
  // data:image/png;base64,XXXX → strip prefix
  const b64 = base64Data.replace(/^data:image\/\w+;base64,/, "");
  const buf = Buffer.from(b64, "base64");
  const filename = `${prefix}-${Date.now()}.png`;
  const outputPath = path.join(os.tmpdir(), filename);
  fs.writeFileSync(outputPath, buf);
  return { path: outputPath, bytes: buf.length };
}

const server = new Server(
  {
    name: "draw-things-mcp",
    version: "0.1.0",
  },
  {
    capabilities: { tools: {} },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "generate_image",
        description:
          "Generate image via Draw Things (SDXL backend). Returns path to PNG on disk + base64 inline. " +
          "Useful when local Draw Things instance is available and you need photorealistic " +
          "documentary-style imagery with LoRA control (e.g. STALKER_SDXL).",
        inputSchema: {
          type: "object",
          properties: {
            prompt: {
              type: "string",
              description: "Text prompt for image generation",
            },
            negative_prompt: {
              type: "string",
              description: "Negative prompt (default: speech bubble, text, watermark, signature)",
            },
            width: { type: "integer", description: "Image width in pixels", default: 1024 },
            height: { type: "integer", description: "Image height in pixels", default: 1024 },
            steps: { type: "integer", description: "Sampling steps", default: 20 },
            sampler: {
              type: "string",
              description: "Sampler name (e.g. 'DPM++ SDE Karras')",
              default: "DPM++ SDE Karras",
            },
            cfg_scale: {
              type: "number",
              description: "Guidance scale (higher = follow prompt more strictly)",
              default: 7,
            },
            seed: {
              type: "integer",
              description: "Seed for reproducibility (random if omitted)",
            },
            lora: {
              type: "string",
              description: "LoRA file name to inject into prompt (e.g. 'STALKER_SDXL.safetensors')",
            },
            lora_weight: {
              type: "number",
              description: "LoRA strength (0.0 - 1.5, default 0.7)",
              default: 0.7,
            },
            prefix: {
              type: "string",
              description: "Filename prefix for saved PNG",
              default: "draw-things",
            },
          },
          required: ["prompt"],
        },
      },
      {
        name: "get_options",
        description:
          "Get current Draw Things options (model, LoRAs, sampler, default resolution, " +
          "last prompt, etc). Useful for debugging or discovering what's loaded.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  log(`CallTool: ${name}, args=${JSON.stringify(args).slice(0, 100)}`);
  process.stderr.write(`[draw-things] DEBUG: CallTool ${name} START\n`);

  try {
    if (name === "get_options") {
      const opts = await fetchOptions();
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                model: opts.model,
                sampler: opts.sampler,
                steps: opts.steps,
                width: opts.width,
                height: opts.height,
                loras: opts.loras,
                default_negative_prompt: opts.negative_prompt?.slice(0, 200),
                last_prompt_snippet: opts.prompt?.slice(0, 200),
              },
              null,
              2
            ),
          },
        ],
      };
    }

    if (name === "generate_image") {
      const prompt = args.prompt;
      const negative_prompt =
        args.negative_prompt ||
        "speech bubble, dialogue bubble, text bubble, thought bubble, text, letters, words, writing, glyphs, characters, symbols, typography, watermark, signature";

      // Если задана LoRA — добавляем в prompt
      let fullPrompt = prompt;
      if (args.lora) {
        fullPrompt = `${prompt} <lora:${args.lora.replace(/\.safetensors$/, "")}:${args.lora_weight || 0.7}>`;
      }

      log(`Generate: ${fullPrompt.slice(0, 80)}...`);

      // Draw Things: один POST /txt2img со всеми параметрами
      // НЕ дёргаем /options — это запускает отдельную задачу и блокирует /txt2img
      const result = await postToDrawThings("/sdapi/v1/txt2img", {
        prompt: fullPrompt,
        negative_prompt,
        width: args.width || 1024,
        height: args.height || 1024,
        steps: args.steps || 20,
        sampler: args.sampler || "DPM++ SDE Karras",
        seed: args.seed || -1,
        cfg_scale: args.cfg_scale || 7,
        batch_size: 1,
        batch_count: 1,
      });

      if (!result.images || result.images.length === 0) {
        throw new Error("Draw Things returned no images");
      }

      const { path: savedPath, bytes } = saveBase64Png(result.images[0], args.prefix);
      const info = result.info ? JSON.parse(result.info) : {};

      log(`Saved ${bytes} bytes to ${savedPath}`);

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                success: true,
                path: savedPath,
                bytes,
                seed: info.seed,
                width: args.width || 1024,
                height: args.height || 1024,
                model: "Draw Things SDXL (sd_xl_base_1.0_f16)",
                prompt: fullPrompt.slice(0, 200),
              },
              null,
              2
            ),
          },
        ],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (err) {
    log(`Error: ${err.message}`);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: false,
              error: err.message,
              hint: err.message.includes("timeout")
                ? "Draw Things busy or unreachable. Try increasing DRAW_THINGS_TIMEOUT or check if another job is running."
                : undefined,
            },
            null,
            2
          ),
        },
      ],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  log(`Started, pointing to ${API_BASE}, timeout ${TIMEOUT_SEC}s`);
}

main().catch((err) => {
  log(`Fatal: ${err.message}`);
  process.exit(1);
});

// Глобальные handlers — ловим всё что упустили, чтобы не падать молча
process.on("uncaughtException", (err) => {
  log(`UncaughtException: ${err.message}`);
});

process.on("unhandledRejection", (reason) => {
  log(`UnhandledRejection: ${reason}`);
});
