import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError
} from "@modelcontextprotocol/sdk/types.js";

const API_BASE_URL = process.env.API_BASE_URL || "http://127.0.0.1:3000";

class ComicStudioMcpServer {
  constructor() {
    this.server = new Server({
      name: "comic-studio-mcp",
      version: "1.0.0"
    }, {
      capabilities: {
        tools: {}
      }
    });

    this.setupHandlers();
  }

  setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "list_scenarios",
            description: "Get a list of comic scenarios",
            inputSchema: {
              type: "object",
              properties: {
                status: {
                  type: "string",
                  description: "Status filter (draft, approved, rejected, rendered, published, all)",
                  enum: ["draft", "approved", "rejected", "rendered", "published", "all"]
                }
              }
            }
          },
          {
            name: "get_scenario",
            description: "Get full details of a specific comic scenario by ID",
            inputSchema: {
              type: "object",
              properties: {
                id: {
                  type: "string",
                  description: "Scenario ID (8 chars hex)"
                }
              },
              required: ["id"]
            }
          },
          {
            name: "create_comic",
            description: "Create a new comic scenario draft from a text prompt",
            inputSchema: {
              type: "object",
              properties: {
                content: {
                  type: "string",
                  description: "The text context/story for the comic"
                },
                image_style: {
                  type: "string",
                  description: "Visual style of the comic (e.g. comic, manga, realistic)"
                },
                caption_style: {
                  type: "string",
                  description: "Caption style (e.g. bubble, star, gothic, boom, memo, bar)"
                },
                panel_count: {
                  type: "integer",
                  description: "Number of panels to generate (3..6, default 3)",
                  minimum: 3,
                  maximum: 6,
                  default: 3
                }
              },
              required: ["content"]
            }
          },
          {
            name: "expand_panels",
            description: "Incrementally expand a draft scenario with additional panels (3..6). Adds one panel at a time via LLM, preserves existing panels. On LLM failure returns fallback with panels unchanged.",
            inputSchema: {
              type: "object",
              properties: {
                id: {
                  type: "string",
                  description: "Scenario ID (8 chars hex)"
                },
                target_count: {
                  type: "integer",
                  description: "Desired final panel count (3..6, must be greater than current)",
                  minimum: 3,
                  maximum: 6
                },
                scene_hints: {
                  type: "array",
                  items: { type: "string" },
                  description: "Optional per-panel hints (one per new panel). Missing hints are filled with empty strings."
                }
              },
              required: ["id", "target_count"]
            }
          },
          {
            name: "approve_scenario",
            description: "Approve a draft scenario for rendering",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string" }
              },
              required: ["id"]
            }
          },
          {
            name: "export_comic_pdf",
            description: "Export a rendered comic into a multi-page PDF document for printing",
            inputSchema: {
              type: "object",
              properties: { id: { type: "string" } },
              required: ["id"]
            }
          },
          {
            name: "export_comic_zip",
            description: "Export a rendered comic into a Social ZIP package (panels + HTML)",
            inputSchema: {
              type: "object",
              properties: { id: { type: "string" } },
              required: ["id"]
            }
          },
          {
            name: "render_comic",
            description: "Start rendering an approved or rendered scenario. Supports provider selection (minimax|draw-things) and auto-publish chain.",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string" },
                mode: { type: "string", enum: ["initial", "rerender"] },
                provider: {
                  type: "string",
                  enum: ["minimax", "draw-things"],
                  default: "minimax",
                  description: "Image generation provider. draw-things requires local SDXL backend."
                },
                publish: {
                  type: "boolean",
                  default: false,
                  description: "If true, automatically publish to site after render completes."
                }
              },
              required: ["id"]
            }
          },
          {
            name: "publish_comic",
            description: "Publish a rendered (or already published) comic to the configured SITE_API_URL. Returns published_url when WEB_PUBLIC_URL is set.",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string", description: "Scenario ID (8 chars hex)" }
              },
              required: ["id"]
            }
          },
          {
            name: "create_book_html",
            description: "Render a knowledge book HTML from a published/rendered scenario. Generates data/comics/<id>-book.html with the chosen style palette and glossary. Available styles: sentry, ramstein, hornsdale, partition, puppet, ai-paradox, stalker.",
            inputSchema: {
              type: "object",
              properties: {
                scenario_id: {
                  type: "string",
                  description: "Scenario ID (8 chars hex)"
                },
                style: {
                  type: "string",
                  enum: ["sentry", "ramstein", "hornsdale", "partition", "puppet", "ai-paradox", "stalker"],
                  description: "Book style (palette + default glossary)"
                },
                title: { type: "string", description: "Override book title (default: scenario title)" },
                subtitle: { type: "string", description: "Override book subtitle" },
                provider: { type: "string", description: "Render provider name shown in footer (default: minimax)" }
              },
              required: ["scenario_id", "style"]
            }
          },
          {
            name: "wait_for_render",
            description: "Poll the web job queue until a render/publish job for the given scenario reaches a terminal state (succeeded/failed/interrupted) or timeout expires. Returns the latest job's status and result. Useful for replacing 'sleep 240 && ls panel_*.png' workflows.",
            inputSchema: {
              type: "object",
              properties: {
                scenario_id: {
                  type: "string",
                  description: "Scenario ID (8 chars hex) to wait for"
                },
                timeout_seconds: {
                  type: "number",
                  description: "Maximum seconds to wait (default 240, max 900)",
                  minimum: 5,
                  maximum: 900,
                  default: 240
                },
                poll_interval_seconds: {
                  type: "number",
                  description: "Seconds between status checks (default 3, min 1, max 10)",
                  minimum: 1,
                  maximum: 10,
                  default: 3
                }
              },
              required: ["scenario_id"]
            }
          },
          {
            name: "revise_scenario",
            description: "Revise a scenario based on text feedback",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string" },
                feedback: { type: "string" }
              },
              required: ["id", "feedback"]
            }
          },
          {
            name: "restyle_comic",
            description: "Change the caption/bubble style of a rendered comic (bubble, star, gothic, boom, memo, bar)",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string" },
                style: { type: "string", enum: ["bubble", "star", "gothic", "boom", "memo", "bar"] }
              },
              required: ["id", "style"]
            }
          },
          {
            name: "resolve_intent",
            description: "Resolve a natural language phrase into a scenario ID (fuzzy search using AiPULT)",
            inputSchema: {
              type: "object",
              properties: {
                phrase: { type: "string" },
                limit: { type: "number", description: "Max number of candidates (default 5)" }
              },
              required: ["phrase"]
            }
          },
          {
            name: "read_comic_image",
            description: "Read a comic image (composite or individual panel) to analyze it visually",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string", description: "Scenario ID" },
                panel: { type: "number", description: "Panel number (e.g. 1, 2, 3). If omitted, returns the composite image." }
              },
              required: ["id"]
            }
          },
          {
            name: "update_comic_text",
            description: "Fast-update the text (captions) or bubble style of a rendered comic WITHOUT re-rendering images. Use this to fix typos, change dialogues, or restyle bubbles instantly.",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string", description: "Scenario ID" },
                style: { type: "string", description: "Optional new bubble style (e.g. bubble, gothic, boom)" },
                captions: {
                  type: "array",
                  items: { type: "string" },
                  description: "Optional array of new text strings for all panels in order"
                }
              },
              required: ["id"]
            }
          }
        ]
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const name = request.params.name;
      const args = request.params.arguments || {};

      try {
        if (name === "list_scenarios") {
          const status = args.status || "all";
          const res = await this.apiFetch(`/api/scenarios?status=${status}`);
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }
        
        if (name === "get_scenario") {
          const res = await this.apiFetch(`/api/scenarios/${args.id}`);
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "create_comic") {
          const body = {
            content: args.content,
            image_style: args.image_style,
            caption_style: args.caption_style,
          };
          if (args.panel_count !== undefined && args.panel_count !== null) {
            body.panel_count = args.panel_count;
          }
          const res = await this.apiFetch(`/api/scenarios`, "POST", body);
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "expand_panels") {
          const body = {
            target_count: args.target_count,
          };
          if (Array.isArray(args.scene_hints) && args.scene_hints.length) {
            body.scene_hints = args.scene_hints;
          }
          const res = await this.apiFetch(`/api/scenarios/${args.id}/expand`, "POST", body);
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "approve_scenario") {
          const res = await this.apiFetch(`/api/scenarios/${args.id}/approve`, "POST");
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "render_comic") {
          const body = {
            mode: args.mode || "initial",
          };
          if (args.provider) body.provider = args.provider;
          if (args.publish !== undefined) body.publish = Boolean(args.publish);
          const res = await this.apiFetch(`/api/scenarios/${args.id}/render`, "POST", body);
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "publish_comic") {
          const res = await this.apiFetch(`/api/scenarios/${args.id}/publish`, "POST", {});
          // After publish job completes, query the published scenario for the URL.
          // Note: the publish is async — for the URL the caller should poll the
          // scenario via get_scenario(id) after the job finishes.
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "create_book_html") {
          const body = {
            style: args.style,
          };
          if (args.title) body.title = args.title;
          if (args.subtitle) body.subtitle = args.subtitle;
          if (args.provider) body.provider = args.provider;
          const res = await this.apiFetch(`/api/scenarios/${args.scenario_id}/book`, "POST", body);
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "wait_for_render") {
          const scenarioId = args.scenario_id;
          const timeoutSeconds = Math.min(Math.max(args.timeout_seconds || 240, 5), 900);
          const pollInterval = Math.min(Math.max(args.poll_interval_seconds || 3, 1), 10);
          const result = await this.waitForRender(scenarioId, { timeoutSeconds, pollInterval });
          return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        }

        if (name === "revise_scenario") {
          const res = await this.apiFetch(`/api/scenarios/${args.id}/revise`, "POST", {
            feedback: [{ text: args.feedback }]
          });
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "restyle_comic") {
          const res = await this.apiFetch(`/api/scenarios/${args.id}/restyle`, "POST", {
            style: args.style
          });
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "resolve_intent") {
          const res = await this.apiFetch(`/api/aipult/resolve`, "POST", {
            phrase: args.phrase,
            limit: args.limit || 5
          });
          return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
        }

        if (name === "read_comic_image") {
          const imagePath = args.panel ? `/comics/${args.id}/panel_${args.panel}.png` : `/comics/${args.id}.png`;
          const url = `${API_BASE_URL}${imagePath}`;
          const res = await fetch(url);
          if (!res.ok) throw new McpError(ErrorCode.InvalidParams, `Image not found or not generated yet: ${imagePath}`);
          const buffer = await res.arrayBuffer();
          const base64 = Buffer.from(buffer).toString("base64");
          return {
            content: [
              {
                type: "image",
                data: base64,
                mimeType: "image/png"
              },
              {
                type: "text",
                text: `Successfully loaded image: ${imagePath}`
              }
            ]
          };
        }

        if (name === "update_comic_text") {
          const res = await this.apiFetch(`/api/scenarios/${args.id}/restyle`, "POST", {
            style: args.style,
            captions: args.captions
          });
          return { content: [{ type: "text", text: `Success! Comic updated instantly. View at ${API_BASE_URL}/comics/${args.id}.html` }] };
        }

        if (name === "export_comic_pdf") {
          const downloadUrl = `${API_BASE_URL}/api/scenarios/${args.id}/export/pdf`;
          return { content: [{ type: "text", text: `PDF export download link: ${downloadUrl}` }] };
        }

        if (name === "export_comic_zip") {
          const downloadUrl = `${API_BASE_URL}/api/scenarios/${args.id}/export/zip`;
          return { content: [{ type: "text", text: `Social ZIP export download link: ${downloadUrl}` }] };
        }

        throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
      } catch (err) {
        if (err instanceof McpError) throw err;
        return {
          content: [{ type: "text", text: `API Error: ${err.message}` }],
          isError: true
        };
      }
    });
  }

  async apiFetch(path, method = "GET", body = null) {
    const url = `${API_BASE_URL}${path}`;
    const init = { method, headers: {} };

    if (body) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }

    // Auth token integration can be added here if the server starts enforcing it
    // process.env.API_TOKEN

    try {
      const res = await fetch(url, init);
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.error?.message || data.error || `HTTP ${res.status}`);
      }
      return data;
    } catch (err) {
      throw err;
    }
  }

  /**
   * Poll the web job queue until a render or publish job for the given scenario
   * reaches a terminal state (succeeded/failed/interrupted) or the timeout
   * expires. Returns a structured result with the latest matching job.
   *
   * Polling strategy:
   *   - On each iteration, fetch all jobs from GET /api/jobs and filter by
   *     scenario_id, keeping only render and publish types
   *   - Find the most recent job by created_at (covers rerender chains)
   *   - If the latest job is terminal, return immediately
   *   - If no job exists yet (e.g. operator just called render_comic), keep
   *     polling — the job will appear in the queue shortly
   *
   * Time complexity: O(N) per poll where N = total jobs in store.
   * For typical workloads (N < 100) this is negligible. For larger stores
   * the web server would need a /api/jobs?scenario_id=X endpoint (out of scope).
   */
  async waitForRender(scenarioId, { timeoutSeconds = 240, pollInterval = 3 } = {}) {
    const terminal = new Set(["succeeded", "failed", "interrupted"]);
    const deadline = Date.now() + timeoutSeconds * 1000;
    const start = Date.now();
    let polls = 0;
    let lastStatus = "no_job_found";
    let lastJob = null;

    while (Date.now() < deadline) {
      polls += 1;
      try {
        const data = await this.apiFetch("/api/jobs");
        const items = Array.isArray(data.items) ? data.items : [];

        // Filter by scenario_id, keep only render/publish types, sort by created_at desc
        const matches = items
          .filter((j) => j && j.scenario_id === scenarioId && (j.type === "render" || j.type === "publish"))
          .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));

        if (matches.length > 0) {
          lastJob = matches[0];
          lastStatus = lastJob.status || "unknown";
          if (terminal.has(lastStatus)) {
            const durationSeconds = (Date.now() - start) / 1000;
            return {
              ok: true,
              timeout: false,
              scenario_id: scenarioId,
              job_id: lastJob.id,
              type: lastJob.type,
              status: lastStatus,
              duration_seconds: Math.round(durationSeconds * 10) / 10,
              polls,
              started_at: lastJob.started_at,
              finished_at: lastJob.finished_at,
              result: lastJob.result,
              error: lastJob.error,
            };
          }
        }
      } catch (pollErr) {
        // Network error — log and keep polling (don't crash mid-wait)
        process.stderr.write(`[wait_for_render] poll error: ${pollErr.message}\n`);
      }

      // Sleep with cancellation respect (bail out if deadline passed)
      const remaining = deadline - Date.now();
      if (remaining <= 0) break;
      await new Promise((resolve) => setTimeout(resolve, Math.min(pollInterval * 1000, remaining)));
    }

    const durationSeconds = (Date.now() - start) / 1000;
    return {
      ok: false,
      timeout: true,
      scenario_id: scenarioId,
      last_status: lastStatus,
      job_id: lastJob ? lastJob.id : null,
      duration_seconds: Math.round(durationSeconds * 10) / 10,
      polls,
      timeout_seconds: timeoutSeconds,
      hint: lastJob
        ? `Job ${lastJob.id} still ${lastStatus}; consider increasing timeout_seconds`
        : "No job appeared for this scenario within the timeout; verify the scenario was rendered before calling wait_for_render",
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    // Keep the process alive — stdio transport maintains the event loop
  }
}

const mcp = new ComicStudioMcpServer();
mcp.run().catch(console.error);
