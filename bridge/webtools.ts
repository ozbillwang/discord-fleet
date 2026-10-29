/**
 * BuilderXAI tools for omp (Bot User agents, loaded by the bridge with an explicit --tools allowlist).
 * - web_search, web_answer, web_fetch: our public TinyFish/Tavily LBs; token from env WEB_CLIENT_TOKEN.
 * - image_generate / image_edit: local bx-llm-gw image routes; model fixed to gpt-image-2.5, n=1; key = CLIAPI_API_KEY.
 *   image_edit takes refs "logo" (BX_LOGO, baked into the image) or "img-N" (member images the bridge saved in BX_IN_DIR).
 *   The image is written to $BX_OUT_DIR and the bridge attaches it to the Discord reply; the model never sees b64.
 * Tokens are never shown to the model.
 */
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const TF_SEARCH = process.env.TINYFISH_SEARCH ?? "https://search.example.com";
const TF_FETCH = process.env.TINYFISH_FETCH ?? "https://fetch.example.com";
const TAVILY = process.env.TAVILY_SERVER ?? "https://answer.example.com";
const IMAGE_GW = process.env.BX_IMAGE_GW ?? "http://10.0.2.2:18080/v1/images/generations";
const IMAGE_EDIT_GW = process.env.BX_IMAGE_EDIT_GW ?? IMAGE_GW.replace(/\/generations$/, "/edits");
const IMAGE_MODEL = "gpt-image-2.5"; // fixed by policy; not a tool parameter
const IMAGE_SIZES = ["1024x1024", "1024x1536", "1536x1024", "auto"] as const;
const TIMEOUT_MS = 45_000;
const IMAGE_TIMEOUT_MS = 240_000;
const MAX_IMAGES_PER_TURN = 2; // matches the bridge's attachment cap; extra calls are refused (no quota spent)
const MAX_WEB_CALLS_PER_TURN = 15; // web_search + web_answer + web_fetch combined, reset on each user message
const MAX_FETCH_CHARS = 20_000;

function token(): string {
	const t = process.env.WEB_CLIENT_TOKEN;
	if (!t) throw new Error("web tools are not configured (WEB_CLIENT_TOKEN missing)");
	return t;
}

async function call(url: string, init: RequestInit): Promise<any> {
	const ctl = new AbortController();
	const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
	try {
		const r = await fetch(url, { ...init, signal: ctl.signal });
		const text = await r.text();
		if (!r.ok) throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
		return JSON.parse(text);
	} finally {
		clearTimeout(timer);
	}
}

const text = (s: string) => ({ content: [{ type: "text" as const, text: s }], details: {} });

export default function (pi: ExtensionAPI) {
	const z = pi.zod;

	// ---- images (independent of WEB_CLIENT_TOKEN): shared slot reservation + gateway call + save
	async function runImage(endpoint: string, payload: Record<string, unknown>, label: string) {
		const key = process.env.CLIAPI_API_KEY;
		const outDir = process.env.BX_OUT_DIR;
		if (!key || !outDir) return text("画图功能未配置，请告诉用户稍后再试。");
		mkdirSync(outDir, { recursive: true });
		// Reserve a slot synchronously (before any await) so parallel tool calls can't all pass the cap.
		const pending = readdirSync(outDir).length;
		if (pending >= MAX_IMAGES_PER_TURN)
			return text(`IMAGE_LIMIT: 本轮已生成或正在生成 ${pending} 张，每次回复最多 ${MAX_IMAGES_PER_TURN} 张，不要再调用画图工具。`);
		const slot = join(outDir, `.pending-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
		writeFileSync(slot, "");
		const ctl = new AbortController();
		const timer = setTimeout(() => ctl.abort(), IMAGE_TIMEOUT_MS);
		try {
			const r = await fetch(endpoint, {
				method: "POST",
				signal: ctl.signal,
				headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
				body: JSON.stringify({ model: IMAGE_MODEL, n: 1, ...payload }),
			});
			const body = await r.text();
			if (r.status === 429 && /quota/i.test(body))
				return text("IMAGE_QUOTA_EXHAUSTED: 今天画图额度用完了。请告诉用户今天画图额度用完了，明天再试。");
			if (!r.ok) return text(`IMAGE_FAILED: ${label}失败（HTTP ${r.status}）。请告诉用户画图失败，请稍后再试。`);
			const b64 = JSON.parse(body)?.data?.[0]?.b64_json;
			if (!b64) return text("IMAGE_FAILED: 没有拿到图片。请告诉用户画图失败，请稍后再试。");
			const file = join(outDir, `${Date.now()}-${Math.random().toString(36).slice(2, 6)}.png`);
			writeFileSync(file, Buffer.from(b64, "base64"));
			return text(
				`图片已${label}，会作为附件发出（模型 ${IMAGE_MODEL}，本次 1 张，本轮第 ${pending + 1} 张）。` +
					"模型和数量由系统固定，不能更改；回复时如实说明，不要声称用了别的模型或画了更多张。用一两句话介绍这张图即可。",
			);
		} catch (e) {
			return text("IMAGE_FAILED: 画图超时或出错。请告诉用户画图失败，请稍后再试。");
		} finally {
			clearTimeout(timer);
			rmSync(slot, { force: true }); // release the reservation on success and on every failure path
		}
	}

	pi.registerTool({
		name: "image_generate",
		label: "Generate image",
		description:
			"Generate ONE image from a TEXT prompt (model and count are fixed by the system). For pictures that must contain " +
			"the BuilderX logo or build on an image the user posted, use image_edit instead. The image is attached to your " +
			"Discord reply automatically; you only get a confirmation back. Write a detailed prompt (subject, style, " +
			"composition, colours, exact text in quotes). SFW only. At most 2 image calls per reply.",
		parameters: z.object({
			prompt: z.string().min(1).max(4000).describe("Detailed image prompt"),
			size: z.enum(IMAGE_SIZES).optional().describe("1024x1024 (default), 1024x1536 portrait, 1536x1024 landscape, or auto"),
		}),
		async execute(_id, p) {
			return runImage(IMAGE_GW, { prompt: p.prompt, size: p.size ?? "1024x1024" }, "生成");
		},
	});

	pi.registerTool({
		name: "image_edit",
		label: "Edit image / use reference",
		description:
			"Create ONE image using 1-2 REFERENCE images: \"logo\" = the official BuilderX AI logo, or an id like \"img-3\" " +
			"for a picture the user posted in this thread (the ids are listed next to the user's message). Use it to put " +
			"the logo on a poster, restyle or modify the user's picture, or combine the two. Describe in the prompt exactly " +
			"what to keep and what to change (e.g. \"place this exact logo in the top-left corner, unchanged\"). Only those " +
			"ids work: no URLs, file paths or web images. Don't search the web for images. Model/count fixed; SFW only; " +
			"at most 2 image calls per reply.",
		parameters: z.object({
			prompt: z.string().min(1).max(4000).describe("What to make, and how to use the reference image(s)"),
			refs: z.array(z.string()).min(1).max(2).describe('Reference ids: "logo" and/or "img-N" from this thread'),
			size: z.enum(IMAGE_SIZES).optional().describe("1024x1024 (default), 1024x1536 portrait, 1536x1024 landscape, or auto"),
		}),
		async execute(_id, p) {
			const images: string[] = [];
			for (const ref of p.refs) {
				let file: string | undefined;
				if (ref === "logo") {
					file = process.env.BX_LOGO;
				} else if (/^img-\d{1,6}$/.test(ref) && process.env.BX_IN_DIR) {
					const dir = process.env.BX_IN_DIR;
					const hit = readdirSync(dir).find((f) => f === `${ref}.png` || f === `${ref}.jpg` || f === `${ref}.webp`);
					file = hit ? join(dir, hit) : undefined;
				}
				if (!file || !existsSync(file))
					return text(
						`IMAGE_REF_UNKNOWN: 找不到参考图 "${ref}"。只能用 "logo" 或本 thread 里用户发的图片编号（img-N）。` +
							"如果用户还没发图，请对方先在 thread 里发图。",
					);
				images.push(readFileSync(file).toString("base64"));
			}
			return runImage(IMAGE_EDIT_GW, { prompt: p.prompt, size: p.size ?? "1024x1024", images }, "生成");
		},
	});

	if (!process.env.WEB_CLIENT_TOKEN) return; // web tools only when their token is configured

	// Per-turn budget for web tools: after MAX_WEB_CALLS_PER_TURN the tools refuse, so the model stops and answers.
	let webCalls = 0;
	pi.on("agent_start", async () => {
		webCalls = 0;
	});
	const overBudget = () => {
		webCalls += 1;
		return webCalls > MAX_WEB_CALLS_PER_TURN
			? text(
					`WEB_BUDGET_EXHAUSTED: 本轮已经调用联网工具 ${MAX_WEB_CALLS_PER_TURN} 次。停止搜索，` +
						"直接用已经拿到的信息回复用户；没找到就如实说没找到，并问用户能否提供更具体的线索。",
				)
			: null;
	};

	pi.registerTool({
		name: "web_search",
		label: "Web search",
		description:
			"Search the web. Returns titles, URLs and snippets. Use for current events, facts, docs, products. " +
			"Then use web_fetch on the most relevant URL if you need the full page.",
		parameters: z.object({
			query: z.string().min(1).max(300).describe("Search query"),
			limit: z.number().int().min(1).max(10).optional().describe("Max results (default 6)"),
		}),
		async execute(_id, p) {
			const stop = overBudget();
			if (stop) return stop;
			const d = await call(`${TF_SEARCH}/?query=${encodeURIComponent(p.query)}`, {
				headers: { "X-API-Key": token(), Accept: "application/json" },
			});
			const rows = (d.results ?? []).slice(0, p.limit ?? 6);
			if (!rows.length) return text(`No results for "${p.query}". Try web_answer or a different query.`);
			return text(
				rows.map((r: any, i: number) => `${i + 1}. ${r.title}\n   ${r.url}\n   ${r.snippet ?? ""}`).join("\n"),
			);
		},
	});

	pi.registerTool({
		name: "web_answer",
		label: "Web answer",
		description:
			"Ask a question and get a short synthesized answer with sources from a web search engine. " +
			"Good for 'what is / who / latest on' questions. Always cite the sources you rely on.",
		parameters: z.object({
			question: z.string().min(1).max(300).describe("The question"),
		}),
		async execute(_id, p) {
			const stop = overBudget();
			if (stop) return stop;
			const d = await call(`${TAVILY}/search`, {
				method: "POST",
				headers: {
					Authorization: `Bearer ${token()}`,
					"Content-Type": "application/json",
					Accept: "application/json",
				},
				body: JSON.stringify({ query: p.question, max_results: 5, include_answer: true }),
			});
			const src = (d.results ?? []).map((r: any, i: number) => `${i + 1}. ${r.title} — ${r.url}`).join("\n");
			return text(`ANSWER: ${d.answer ?? "(none)"}\n\nSOURCES:\n${src}`);
		},
	});

	pi.registerTool({
		name: "web_fetch",
		label: "Read web page",
		description:
			"Read a public web page and return its main text as markdown (truncated to ~20k chars). " +
			"Use after web_search to read a specific result. Login-walled sites (x.com, WeChat, Xiaohongshu) won't work.",
		parameters: z.object({
			url: z.string().url().max(2000).describe("Absolute http(s) URL"),
		}),
		async execute(_id, p) {
			if (!/^https?:\/\//i.test(p.url)) return text("Only http(s) URLs are supported.");
			const stop = overBudget();
			if (stop) return stop;
			const d = await call(`${TF_FETCH}/`, {
				method: "POST",
				headers: { "X-API-Key": token(), "Content-Type": "application/json", Accept: "application/json" },
				body: JSON.stringify({ urls: [p.url], format: "markdown" }),
			});
			const r = (d.results ?? [])[0];
			if (!r || !r.text) return text(`Could not read ${p.url}${d.errors?.length ? `: ${JSON.stringify(d.errors).slice(0, 200)}` : ""}`);
			let body: string = String(r.text).replace(/\\_/g, "_");
			if (body.length > MAX_FETCH_CHARS) body = body.slice(0, MAX_FETCH_CHARS) + "\n\n[truncated]";
			return text(`# ${r.title ?? p.url}\n${r.final_url ?? p.url}\n\n${body}`);
		},
	});
}
