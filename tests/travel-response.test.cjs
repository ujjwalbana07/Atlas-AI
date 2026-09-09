const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const context = vm.createContext({
    localStorage: { getItem: () => null },
    document: { addEventListener: () => {} },
});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../static/script.js"), "utf8"), context);
const readResponse = (body, status = 200) => context.readTravelResponse(new Response(body, { status }));

test("Live Server uses FastAPI while other deployments use their own origin", () => {
    for (const hostname of ["localhost", "127.0.0.1"]) {
        assert.equal(context.travelApiUrl({ hostname, port: "5500" }), "http://127.0.0.1:8000/api/travel");
        assert.equal(context.travelApiUrl({ hostname, port: "8000" }), "/api/travel");
    }
    assert.equal(context.travelApiUrl({ hostname: "travel.example.com", port: "" }), "/api/travel");
});

test("accepts a complete travel plan", async () => {
    const data = await readResponse(JSON.stringify({ success: true, answer: "A trip", thread_id: "trip-1" }));
    assert.equal(data.answer, "A trip");
    assert.equal(data.thread_id, "trip-1");
});

test("empty responses identify the HTTP status and FastAPI server", async () => {
    for (const status of [200, 502, 504]) {
        await assert.rejects(readResponse("", status), new RegExp(`empty response \\(HTTP ${status}\\).*FastAPI`));
    }
});

test("HTML and truncated JSON produce useful errors", async () => {
    for (const body of ["<html>Bad gateway</html>", '{"success":']) {
        await assert.rejects(readResponse(body, 502), /invalid response \(HTTP 502\)/);
    }
});

test("preserves backend errors and FastAPI validation details", async () => {
    await assert.rejects(readResponse('{"success":false,"error":"Service unavailable"}', 500), /Service unavailable \(HTTP 500\)/);
    await assert.rejects(readResponse('{"detail":[{"msg":"Field required"}]}', 422), /Field required \(HTTP 422\)/);
});

test("rejects null and incomplete success payloads", async () => {
    await assert.rejects(readResponse("null"), /request failed/);
    for (const data of [{ success: true }, { success: true, answer: "Plan", thread_id: null }]) {
        await assert.rejects(readResponse(JSON.stringify(data)), /incomplete plan/);
    }
});
