#!/usr/bin/env node

const fs = require("fs");
const { chromium } = require("playwright");

const targetUrl = process.argv[2];
const savePath = process.argv[3];
const linkPattern = process.argv[4];

if (!targetUrl || !savePath) {
    process.exit(1);
}

function getChromiumExecutablePath() {
    const candidates = [
        process.env.CHROMIUM_EXECUTABLE,
        "/usr/bin/chromium-headless-shell",
        "/usr/lib/chromium/chromium-headless-shell",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ].filter(Boolean);

    for (const path of candidates) {
        if (fs.existsSync(path)) {
            return path;
        }
    }

    throw new Error(`Chromium executable not found in ${candidates.join(", ")}`);
}

function isDownloadStartingError(error) {
    return error.message.includes("Download is starting");
}

(async () => {
    let browser = null;

    try {
        browser = await chromium.launch({
            headless: true,
            executablePath: getChromiumExecutablePath(),
            args: [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        });

        const context = await browser.newContext({
            // 实测不需要
            // userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        });

        // 参考文档
        // https://playwright.dev/docs/downloads
        // https://playwright.dev/docs/api/class-download

        const page = await context.newPage();
        let downloadPromise;

        if (linkPattern) {
            await page.goto(targetUrl, { waitUntil: "domcontentloaded" });
            console.error("Page opened:", targetUrl);

            await page.waitForFunction(
                (source) => Array.from(document.querySelectorAll("a[href]")).some((link) => {
                    const pattern = new RegExp(source, "i");
                    const text = (link.textContent || "").trim();
                    const filename = new URL(link.href).pathname.split("/").pop();

                    return pattern.test(link.href) || pattern.test(filename) || pattern.test(text);
                }),
                linkPattern,
                { timeout: 180000 },
            );

            const href = await page.$$eval(
                "a[href]",
                (links, source) => {
                    const link = links.find((item) => {
                        const pattern = new RegExp(source, "i");
                        const text = (item.textContent || "").trim();
                        const filename = new URL(item.href).pathname.split("/").pop();

                        return pattern.test(item.href) || pattern.test(filename) || pattern.test(text);
                    });

                    return link ? link.href : null;
                },
                linkPattern,
            );

            if (!href) {
                throw new Error(`Download link not found: ${linkPattern}`);
            }

            downloadPromise = page.waitForEvent("download", { timeout: 60000 });
            await page.goto(href, { waitUntil: "commit" }).catch((e) => {
                if (!isDownloadStartingError(e)) {
                    throw e;
                }
            });
            console.error("Link opened:", href);
        } else {
            downloadPromise = page.waitForEvent("download", { timeout: 60000 });
            await page.goto(targetUrl, { waitUntil: "commit" }).catch((e) => {
                // 下载直链会触发 'Download is starting' 异常，要手动忽略
                // https://github.com/microsoft/playwright/blob/v1.60.0/tests/library/download.spec.ts#L68
                if (!isDownloadStartingError(e)) {
                    throw e;
                }
            });
            console.error("Page opened:", targetUrl);
        }

        const download = await downloadPromise;
        const suggestedFilename = download.suggestedFilename();
        console.error("Download started:", suggestedFilename, savePath);

        await download.saveAs(savePath);
        console.error("Download completed:", suggestedFilename, savePath);
    } catch (err) {
        console.error("Download failed:", err);
        process.exitCode = 1;
    } finally {
        if (browser) {
            await browser.close();
        }
    }
})();
