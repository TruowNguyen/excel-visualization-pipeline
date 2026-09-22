"""Temporary CDP QA for the local desktop demo build and real workbook."""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from urllib.request import urlopen

import websockets


PORT = 9231
APP = "http://127.0.0.1:8766/"
WORKBOOK = Path(r"D:\task\test data for CX report dashboard.xlsx")
OUTPUT = Path(r"C:\Users\asus\AppData\Local\Temp\evp-demo-qa-25647bf8ee2f4ed5a36490592e2d94cc")


async def main() -> None:
    with urlopen(f"http://127.0.0.1:{PORT}/json/list") as response:
        pages = json.load(response)
    page = next(p for p in pages if p.get("type") == "page" and p.get("url") == APP)
    async with websockets.connect(page["webSocketDebuggerUrl"], max_size=20_000_000) as socket:
        next_id = 0

        async def command(method: str, params: dict | None = None) -> dict:
            nonlocal next_id
            next_id += 1
            identifier = next_id
            await socket.send(json.dumps({"id": identifier, "method": method, "params": params or {}}))
            while True:
                result = json.loads(await socket.recv())
                if result.get("id") != identifier:
                    continue
                if "error" in result:
                    raise RuntimeError(result["error"])
                return result.get("result", {})

        async def evaluate(expression: str):
            result = await command("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
            if "exceptionDetails" in result:
                raise RuntimeError(result["exceptionDetails"])
            return result["result"].get("value")

        async def wait_for(expression: str, timeout: float = 60):
            for _ in range(int(timeout * 5)):
                result = await evaluate(expression)
                if result:
                    return result
                await asyncio.sleep(.2)
            body = await evaluate("document.body.innerText.slice(0, 1300)")
            raise AssertionError(f"Timed out: {expression}\n{body}")

        async def viewport(width: int, height: int):
            await command("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
            await asyncio.sleep(.7)

        async def screenshot(name: str):
            result = await command("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            target = OUTPUT / name
            target.write_bytes(base64.b64decode(result["data"]))
            return str(target)

        async def plot_metrics():
            return await evaluate("""(() => {
              const cards = [...document.querySelectorAll('.chart-grid.children-grid .chart-card')];
              const plots = [...document.querySelectorAll('.chart-grid.children-grid [data-plot]')];
              const rect = el => { const r=el.getBoundingClientRect(); return {x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)} };
              return {width:innerWidth, bodyOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth,
                cardCount:cards.length, cards:cards.slice(0,3).map(rect),
                plots:plots.slice(0,2).map(p => ({rect:rect(p), traces:p.data?.length||0, axis:p.querySelectorAll('.xtick text,.ytick text').length,
                  legend:p.querySelectorAll('.legend text').length, modebar:!!p.querySelector('.modebar')}))};
            })()""")

        await viewport(1024, 768)
        await evaluate("location.reload()")
        await wait_for("document.body.innerText.includes('Chưa có dữ liệu đã nhập')")
        no_data = await screenshot("01-no-data-1024.png")
        await evaluate("document.querySelector('[data-tab=import]').click()")
        await wait_for("!!document.querySelector('#file-input')")
        document = await command("DOM.getDocument")
        node = await command("DOM.querySelector", {"nodeId": document["root"]["nodeId"], "selector": "#file-input"})
        await command("DOM.setFileInputFiles", {"nodeId": node["nodeId"], "files": [str(WORKBOOK)]})
        await wait_for("!!document.querySelector('#preview-action:not(:disabled)')")
        await evaluate("document.querySelector('#preview-action').click()")
        await wait_for("document.querySelector('.preview-status')?.textContent?.includes('Đạt kiểm tra')", timeout=120)
        preview = await screenshot("02-preview-1024.png")
        await evaluate("document.querySelector('[data-action=commit]').click()")
        await wait_for("document.querySelector('#import-result')?.textContent?.includes('Đã nhập workbook')", timeout=120)
        committed = await screenshot("03-committed-1024.png")

        await evaluate("document.querySelector('[data-tab=overview]').click()")
        await wait_for("document.querySelector('[data-field=scope]')?.options.length === 2")
        await evaluate("(() => {const s=document.querySelector('[data-field=scope]');s.value='children';s.dispatchEvent(new Event('change',{bubbles:true}));return true})()")
        await wait_for("document.querySelectorAll('.chart-grid.children-grid .chart-card').length >= 2", timeout=120)
        await wait_for("[...document.querySelectorAll('.chart-grid.children-grid [data-plot]')].every(p => p.data?.length)")
        widths = [(1024, 768), (1366, 768), (1440, 900), (1920, 1080)]
        layout = []
        for width, height in widths:
            await viewport(width, height)
            metrics = await plot_metrics()
            metrics["screenshot"] = await screenshot(f"04-children-{width}.png")
            assert not metrics["bodyOverflow"], metrics
            assert metrics["cardCount"] >= 2 and all(p["axis"] and p["legend"] and p["modebar"] for p in metrics["plots"]), metrics
            if width >= 1366:
                assert metrics["cards"][0]["y"] == metrics["cards"][1]["y"], metrics
            else:
                assert metrics["cards"][0]["y"] < metrics["cards"][1]["y"], metrics
            layout.append(metrics)

        await viewport(1366, 768)
        original = await evaluate("""(() => {const p=document.querySelector('.children-grid [data-plot]');return {mode:document.querySelector('[data-field=mode]').value,
          scope:document.querySelector('[data-field=scope]').value,entity:document.querySelector('[data-field=entity]').value,
          xRange:p._fullLayout?.xaxis?.range?.map(String)}})()""")
        await evaluate("""(() => {const p=document.querySelector('.children-grid [data-plot]');const curve=p.data.findIndex(t=>t.meta?.lineage?.kind==='exact-observation'&&t.meta.lineage.selectable);const point=p.data[curve].ids.findIndex(Boolean);
          p.emit('plotly_click',{points:[{curveNumber:curve,pointNumber:point,x:p.data[curve].x[point],y:p.data[curve].y[point]}]});return true})()""")
        await wait_for("document.querySelector('#investigation-drawer')?.textContent?.includes('Nguồn Excel')")
        drawer = await plot_metrics()
        drawer["screenshot"] = await screenshot("05-drawer-1366.png")
        assert drawer["cards"][0]["y"] < drawer["cards"][1]["y"], drawer
        await evaluate("document.querySelector('[data-action=open-exact-audit]').click()")
        await wait_for("!!document.querySelector('#focused-audit-row')")
        audit = await screenshot("06-audit-1366.png")
        await evaluate("document.querySelector('[data-action=return-to-chart]').click()")
        await wait_for("!!document.querySelector('.children-grid [data-plot]')")
        after_return = await evaluate("""(() => {const p=document.querySelector('.children-grid [data-plot]');return {mode:document.querySelector('[data-field=mode]').value,
          scope:document.querySelector('[data-field=scope]').value,entity:document.querySelector('[data-field=entity]').value,
          xRange:p._fullLayout?.xaxis?.range?.map(String),drawer:document.querySelector('#investigation-drawer').getAttribute('aria-hidden')}})()""")
        await evaluate("document.querySelector('[data-action=close-investigation]').click()")
        await wait_for("document.querySelector('#investigation-drawer')?.getAttribute('aria-hidden')==='true'")
        closed = await plot_metrics()
        assert closed["cards"][0]["y"] == closed["cards"][1]["y"], closed
        assert original["mode"] == after_return["mode"] and original["scope"] == after_return["scope"] and original["entity"] == after_return["entity"]
        assert original["xRange"] == after_return["xRange"], (original, after_return)
        await evaluate("document.querySelector('[data-tab=history]').click()")
        await wait_for("document.body.innerText.includes('test data for CX report dashboard.xlsx')")
        history = await screenshot("07-history-1366.png")
        print(json.dumps({"status": "passed", "screenshots": [no_data, preview, committed, audit, history], "layout": layout, "drawer": drawer, "restoration": {"before": original, "afterAudit": after_return}}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
